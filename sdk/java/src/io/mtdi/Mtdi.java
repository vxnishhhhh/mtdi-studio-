package io.mtdi;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * MTDI Java SDK (Java 11+, no dependencies).
 *
 * <pre>
 *   String line = new Mtdi.Line().add("TEMP", 21.4).seq(7).toString();   // TEMP=21.4,_SEQ=7
 *   Map&lt;String, Double&gt; v = Mtdi.parseLine("TEMP=21.4");             // throws ProtocolException
 *   Mtdi.Result r = new Mtdi.Ewma().update(x);                            // r.score, r.anomaly
 *   new Mtdi.StudioClient("https://x.vercel.app", token).send(Map.of("ch2", 3.1));
 * </pre>
 *
 * Protocol rules and detectors match the Python package number for number
 * (tests/test_sdks.py checks it).
 */
public final class Mtdi {
    private Mtdi() {}

    private static final Pattern KEY = Pattern.compile("^[A-Za-z_][A-Za-z0-9_.\\-]{0,47}$");
    private static final Pattern NUMBER = Pattern.compile("^[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$");

    public static final class ProtocolException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public ProtocolException(String m) { super(m); }
    }

    /** Parse one KEY=value,KEY=value line; the whole line is rejected if any field is malformed. */
    public static Map<String, Double> parseLine(String line) {
        String text = line == null ? "" : line.strip();
        if (text.isEmpty()) throw new ProtocolException("empty line");
        if (text.length() > 2048) throw new ProtocolException("line too long");
        Map<String, Double> out = new LinkedHashMap<>();
        for (String field : text.split(",", -1)) {
            int eq = field.indexOf('=');
            if (eq < 0) throw new ProtocolException("malformed field '" + field + "'");
            String key = field.substring(0, eq).strip(), raw = field.substring(eq + 1).strip();
            if (!KEY.matcher(key).matches() || !NUMBER.matcher(raw).matches())
                throw new ProtocolException("malformed field '" + field + "'");
            if (out.containsKey(key)) throw new ProtocolException("duplicate key " + key);
            double v = Double.parseDouble(raw);
            if (!Double.isFinite(v)) throw new ProtocolException(key + " is not finite");
            out.put(key, v);
        }
        return out;
    }

    /** Builds one protocol line. */
    public static final class Line {
        private final List<String> fields = new ArrayList<>();

        public Line add(String key, double value) {
            if (!KEY.matcher(key).matches()) throw new ProtocolException("invalid key " + key);
            if (!Double.isFinite(value)) throw new ProtocolException(key + " is not finite");
            fields.add(key + "=" + format(value));
            return this;
        }

        public Line seq(long n) { fields.add("_SEQ=" + n); return this; }

        public Line millis(long ms) { fields.add("_T=" + ms); return this; }

        @Override public String toString() { return String.join(",", fields); }

        /** Integers bare, everything else like C's %.6g (matches Python and C++). */
        static String format(double v) {
            if (Math.floor(v) == v && Math.abs(v) < 1e15) return Long.toString((long) v);
            String s = String.format(Locale.ROOT, "%.6g", v);
            if (s.contains("e")) {
                String[] p = s.split("e");
                String mant = p[0].contains(".") ? p[0].replaceAll("0+$", "").replaceAll("\\.$", "") : p[0];
                int exp = Integer.parseInt(p[1]);
                return mant + "e" + (exp < 0 ? "-" : "+") + String.format(Locale.ROOT, "%02d", Math.abs(exp));
            }
            return s.contains(".") ? s.replaceAll("0+$", "").replaceAll("\\.$", "") : s;
        }
    }

    public static final class Result {
        public final double score;
        public final boolean anomaly;
        Result(double score, boolean anomaly) { this.score = score; this.anomaly = anomaly; }
    }

    /** Exponentially weighted mean and variance (mtdi.ml.EWMA). */
    public static final class Ewma {
        private final double alpha, threshold;
        private final int warmup;
        private int n;
        private boolean started;
        private double mean, var;

        public Ewma() { this(0.05, 3.0, 20); }
        public Ewma(double alpha, double threshold, int warmup) { this.alpha = alpha; this.threshold = threshold; this.warmup = warmup; }

        public Result update(double x) {
            n++;
            if (!started) { started = true; mean = x; return new Result(0, false); }
            double sd = Math.sqrt(var);
            double score = sd == 0 ? 0.0 : (x - mean) / sd;
            boolean anomaly = n > warmup && Math.abs(score) >= threshold;
            if (!anomaly) {
                double delta = x - mean;
                mean += alpha * delta;
                var = (1 - alpha) * (var + alpha * delta * delta);
            }
            return new Result(score, anomaly);
        }
    }

    /** Two-sided CUSUM on z-scores of the warm-up reference (mtdi.ml.CUSUM). */
    public static final class Cusum {
        private final double k, h;
        private final int warmup;
        private final List<Double> ref = new ArrayList<>();
        private boolean ready;
        private double mean, sd = 1, pos, neg;

        public Cusum() { this(0.5, 8.0, 100); }
        public Cusum(double drift, double threshold, int warmup) { this.k = drift; this.h = threshold; this.warmup = warmup; }

        public Result update(double x) {
            if (!ready) {
                ref.add(x);
                if (ref.size() >= warmup) {
                    double s = 0;
                    for (double v : ref) s += v;
                    mean = s / ref.size();
                    double ss = 0;
                    for (double v : ref) ss += (v - mean) * (v - mean);
                    sd = Math.sqrt(ss / ref.size());
                    if (sd == 0) sd = 1e-12;
                    ready = true;
                }
                return new Result(0, false);
            }
            double z = (x - mean) / sd;
            pos = Math.max(0, pos + z - k);
            neg = Math.max(0, neg - z - k);
            double score = Math.max(pos, neg);
            boolean anomaly = pos >= h || neg >= h;
            if (anomaly) { pos = 0; neg = 0; }
            return new Result(score, anomaly);
        }
    }

    /** Posts samples to a studio's /api/ingest (ch1: number or [x,y,z], ch2: number, ch3: {x:[...], y:[...]}). */
    public static final class StudioClient {
        private final String base, token;
        private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();

        public StudioClient(String baseUrl, String token) {
            this.base = baseUrl.replaceAll("/+$", "");
            this.token = token;
        }

        public String send(Map<String, Object> sample) throws Exception {
            HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + "/api/ingest"))
                .timeout(Duration.ofSeconds(15))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(Json.write(sample)));
            if (token != null && !token.isEmpty()) b.header("Authorization", "Bearer " + token);
            HttpResponse<String> r = http.send(b.build(), HttpResponse.BodyHandlers.ofString());
            if (r.statusCode() >= 300) throw new RuntimeException("studio refused (" + r.statusCode() + "): " + r.body());
            return r.body();
        }
    }

    /** Minimal JSON writer for maps, lists, numbers, strings and booleans. */
    static final class Json {
        static String write(Object o) {
            if (o == null) return "null";
            if (o instanceof Number || o instanceof Boolean) return o.toString();
            if (o instanceof String) {
                StringBuilder s = new StringBuilder("\"");
                for (char c : ((String) o).toCharArray()) {
                    if (c == '"' || c == '\\') s.append('\\').append(c);
                    else if (c < 0x20) s.append(String.format("\\u%04x", (int) c));
                    else s.append(c);
                }
                return s.append('"').toString();
            }
            if (o instanceof Map) {
                StringBuilder s = new StringBuilder("{");
                boolean first = true;
                for (Map.Entry<?, ?> e : ((Map<?, ?>) o).entrySet()) {
                    if (!first) s.append(',');
                    first = false;
                    s.append(write(String.valueOf(e.getKey()))).append(':').append(write(e.getValue()));
                }
                return s.append('}').toString();
            }
            if (o instanceof Iterable) {
                StringBuilder s = new StringBuilder("[");
                boolean first = true;
                for (Object v : (Iterable<?>) o) {
                    if (!first) s.append(',');
                    first = false;
                    s.append(write(v));
                }
                return s.append(']').toString();
            }
            if (o instanceof double[]) {
                List<Double> l = new ArrayList<>();
                for (double d : (double[]) o) l.add(d);
                return write(l);
            }
            throw new IllegalArgumentException("cannot write " + o.getClass());
        }
    }
}

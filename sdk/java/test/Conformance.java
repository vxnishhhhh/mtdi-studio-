import io.mtdi.Mtdi;
import java.util.Map;

/** Conformance output for tests/test_sdks.py (same inputs as sdk/cpp/conformance.cpp). */
public class Conformance {
    public static void main(String[] args) throws Exception {
        Mtdi.Ewma e = new Mtdi.Ewma();
        Mtdi.Cusum c = new Mtdi.Cusum();
        for (int i = 0; i < 400; i++) {
            double x = Math.sin(i * 0.37) * 2.0 + (i >= 250 ? 3.0 : 0.0) + (i == 120 ? 9.0 : 0.0);
            Mtdi.Result a = e.update(x), b = c.update(x);
            System.out.println("D " + i + " " + a.score + " " + (a.anomaly ? 1 : 0) + " " + b.score + " " + (b.anomaly ? 1 : 0));
        }
        String[] lines = {"CH1=512,CH2=498", "A=1.5e3, B=-.25", "A=1,A=2", "A=", "1A=3", "A=nan", "A=1,", "X=+7."};
        for (String l : lines) {
            try {
                Map<String, Double> v = new java.util.TreeMap<>(Mtdi.parseLine(l));
                StringBuilder s = new StringBuilder("P OK");
                for (Map.Entry<String, Double> kv : v.entrySet()) s.append(" ").append(kv.getKey()).append("=").append(fmt(kv.getValue()));
                System.out.println(s);
            } catch (Mtdi.ProtocolException ex) {
                System.out.println("P ERR");
            }
        }
        System.out.println("L " + new Mtdi.Line().add("TEMP", 21.4).add("N", 40).add("TINY", 0.000123456789).seq(7));
        if (args.length == 2) System.out.println("S " + new Mtdi.StudioClient(args[0], args[1]).send(Map.of("ch2", 3.5, "source", "JAVA")));
    }

    static String fmt(double v) { return v == Math.floor(v) ? Long.toString((long) v) : Double.toString(v); }
}

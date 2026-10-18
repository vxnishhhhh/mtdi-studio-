// MTDI C++ SDK: header-only, C++17, no dependencies.
//
//   #include "mtdi.hpp"
//   mtdi::Line line;  line.add("TEMP", 21.4).add("HUM", 40).seq(17);
//   std::cout << line.str() << "\n";                 // TEMP=21.4,HUM=40,_SEQ=17
//   auto values = mtdi::parse_line("TEMP=21.4");     // throws mtdi::ProtocolError
//   mtdi::Ewma ewma;  auto r = ewma.update(x);       // r.score, r.anomaly
//
// The protocol rules and the detectors match the Python package (mtdi/protocol.py,
// mtdi/ml/anomaly.py) number for number; tests/test_sdks.py checks that.
// For 8-bit Arduino boards use firmware/mtdi_template_arduino instead (no STL there).
#pragma once
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace mtdi {

struct ProtocolError : std::runtime_error {
  explicit ProtocolError(const std::string& m) : std::runtime_error(m) {}
};

inline bool valid_key(const std::string& k) {
  if (k.empty() || k.size() > 48) return false;
  if (!(std::isalpha((unsigned char)k[0]) || k[0] == '_')) return false;
  for (char c : k)
    if (!(std::isalnum((unsigned char)c) || c == '_' || c == '.' || c == '-')) return false;
  return true;
}

// [+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?
inline bool valid_number(const std::string& s) {
  size_t i = 0, n = s.size();
  if (i < n && (s[i] == '+' || s[i] == '-')) i++;
  size_t digits = 0, frac = 0;
  while (i < n && std::isdigit((unsigned char)s[i])) { i++; digits++; }
  if (i < n && s[i] == '.') { i++; while (i < n && std::isdigit((unsigned char)s[i])) { i++; frac++; } }
  if (digits == 0 && frac == 0) return false;
  if (i < n && (s[i] == 'e' || s[i] == 'E')) {
    i++;
    if (i < n && (s[i] == '+' || s[i] == '-')) i++;
    size_t exp = 0;
    while (i < n && std::isdigit((unsigned char)s[i])) { i++; exp++; }
    if (exp == 0) return false;
  }
  return i == n;
}

inline std::string trim(const std::string& s) {
  size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
  return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

// KEY=value,KEY=value lines (JSON lines are accepted by the Python side; firmware sends KEY=value).
inline std::map<std::string, double> parse_line(const std::string& line) {
  std::string text = trim(line);
  if (text.empty()) throw ProtocolError("empty line");
  if (text.size() > 2048) throw ProtocolError("line too long");
  std::map<std::string, double> out;
  std::stringstream ss(text);
  std::string field;
  while (std::getline(ss, field, ',')) {
    size_t eq = field.find('=');
    if (eq == std::string::npos) throw ProtocolError("malformed field '" + field + "'");
    std::string key = trim(field.substr(0, eq)), raw = trim(field.substr(eq + 1));
    if (!valid_key(key) || !valid_number(raw)) throw ProtocolError("malformed field '" + field + "'");
    if (out.count(key)) throw ProtocolError("duplicate key " + key);
    double v = std::strtod(raw.c_str(), nullptr);
    if (!std::isfinite(v)) throw ProtocolError(key + " is not finite");
    out[key] = v;
  }
  if (!text.empty() && text.back() == ',') throw ProtocolError("malformed field ''");
  return out;
}

class Line {
 public:
  Line& add(const std::string& key, double value) {
    if (!valid_key(key)) throw ProtocolError("invalid key " + key);
    if (!std::isfinite(value)) throw ProtocolError(key + " is not finite");
    fields_.emplace_back(key, format(value));
    return *this;
  }
  Line& seq(unsigned long n) { fields_.emplace_back("_SEQ", std::to_string(n)); return *this; }
  Line& millis(unsigned long ms) { fields_.emplace_back("_T", std::to_string(ms)); return *this; }
  std::string str() const {
    std::string out;
    for (size_t i = 0; i < fields_.size(); i++) out += (i ? "," : "") + fields_[i].first + "=" + fields_[i].second;
    return out;
  }
  static std::string format(double v) {  // same as Python's _fmt: integers bare, else %.6g
    if (std::floor(v) == v && std::fabs(v) < 1e15) return std::to_string((long long)v);
    char buf[32];
    std::snprintf(buf, sizeof buf, "%.6g", v);
    return buf;
  }

 private:
  std::vector<std::pair<std::string, std::string>> fields_;
};

struct Result {
  double score = 0;
  bool anomaly = false;
};

// Welford running mean and population standard deviation.
class RunningStats {
 public:
  void add(double x) { n_++; double d = x - mean_; mean_ += d / n_; m2_ += d * (x - mean_); }
  size_t count() const { return n_; }
  double mean() const { return mean_; }
  double sd() const { return n_ ? std::sqrt(m2_ / n_) : 0.0; }

 private:
  size_t n_ = 0;
  double mean_ = 0, m2_ = 0;
};

// Exponentially weighted mean and variance (mtdi.ml.EWMA).
class Ewma {
 public:
  explicit Ewma(double alpha = 0.05, double threshold = 3.0, int warmup = 20)
      : alpha_(alpha), threshold_(threshold), warmup_(warmup) {}
  Result update(double x) {
    n_++;
    if (!started_) { started_ = true; mean_ = x; return {}; }
    double sd = std::sqrt(var_);
    Result r;
    r.score = sd == 0 ? 0.0 : (x - mean_) / sd;
    r.anomaly = n_ > warmup_ && std::fabs(r.score) >= threshold_;
    if (!r.anomaly) {
      double delta = x - mean_;
      mean_ += alpha_ * delta;
      var_ = (1 - alpha_) * (var_ + alpha_ * delta * delta);
    }
    return r;
  }

 private:
  double alpha_, threshold_;
  int warmup_, n_ = 0;
  bool started_ = false;
  double mean_ = 0, var_ = 0;
};

// Two-sided CUSUM on z-scores of the warm-up reference (mtdi.ml.CUSUM).
class Cusum {
 public:
  explicit Cusum(double drift = 0.5, double threshold = 8.0, int warmup = 100)
      : k_(drift), h_(threshold), warmup_(warmup) {}
  Result update(double x) {
    if (!ready_) {
      ref_.push_back(x);
      if ((int)ref_.size() >= warmup_) {
        double sum = 0;
        for (double v : ref_) sum += v;
        mean_ = sum / ref_.size();
        double ss = 0;
        for (double v : ref_) ss += (v - mean_) * (v - mean_);
        sd_ = std::sqrt(ss / ref_.size());
        if (sd_ == 0) sd_ = 1e-12;
        ready_ = true;
      }
      return {};
    }
    double z = (x - mean_) / sd_;
    pos_ = std::max(0.0, pos_ + z - k_);
    neg_ = std::max(0.0, neg_ - z - k_);
    Result r;
    r.score = std::max(pos_, neg_);
    r.anomaly = pos_ >= h_ || neg_ >= h_;
    if (r.anomaly) pos_ = neg_ = 0;
    return r;
  }

 private:
  double k_, h_;
  int warmup_;
  bool ready_ = false;
  std::vector<double> ref_;
  double mean_ = 0, sd_ = 1, pos_ = 0, neg_ = 0;
};

}  // namespace mtdi

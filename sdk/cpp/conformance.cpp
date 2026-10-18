// Conformance output for tests/test_sdks.py: the same inputs every SDK must agree on.
#include <cmath>
#include <iostream>

#include "mtdi.hpp"

int main() {
  mtdi::Ewma e;
  mtdi::Cusum c;
  std::cout.precision(17);
  for (int i = 0; i < 400; i++) {
    double x = std::sin(i * 0.37) * 2.0 + (i >= 250 ? 3.0 : 0.0) + (i == 120 ? 9.0 : 0.0);
    auto a = e.update(x);
    auto b = c.update(x);
    std::cout << "D " << i << " " << a.score << " " << a.anomaly << " " << b.score << " " << b.anomaly << "\n";
  }
  const char* lines[] = {"CH1=512,CH2=498", "A=1.5e3, B=-.25", "A=1,A=2", "A=", "1A=3", "A=nan", "A=1,", "X=+7."};
  for (const char* l : lines) {
    try {
      auto v = mtdi::parse_line(l);
      std::cout << "P OK";
      for (auto& kv : v) std::cout << " " << kv.first << "=" << kv.second;
      std::cout << "\n";
    } catch (const mtdi::ProtocolError&) {
      std::cout << "P ERR\n";
    }
  }
  std::cout << "L " << mtdi::Line().add("TEMP", 21.4).add("N", 40).add("TINY", 0.000123456789).seq(7).str() << "\n";
}

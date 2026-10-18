// Build: g++ -std=c++17 -O2 -I sdk/cpp sdk/cpp/example.cpp -o mtdi_example
// Prints MTDI lines on stdout; pipe them into MTDI with a "process" source:
//   {"id": "cpp", "adapter": "process", "command": ["./mtdi_example"]}
#include <chrono>
#include <cmath>
#include <iostream>
#include <thread>

#include "mtdi.hpp"

int main(int argc, char** argv) {
  int count = argc > 1 ? std::atoi(argv[1]) : 0;   // 0 = run forever
  mtdi::Ewma watch(0.05, 4.0);
  for (unsigned long i = 0; count == 0 || (int)i < count; i++) {
    double level = 20.0 + 2.0 * std::sin(i * 0.1);
    auto r = watch.update(level);
    std::cout << mtdi::Line().add("LEVEL", level).add("SCORE", r.score).seq(i).str() << std::endl;
    if (count == 0) std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }
}

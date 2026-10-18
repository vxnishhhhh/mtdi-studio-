function [score, anomaly] = ewma(x, alpha, threshold, warmup)
%MTDI.EWMA Exponentially weighted anomaly scores for a whole series.
%   [score, anomaly] = mtdi.ewma(x)                      alpha 0.05, threshold 3, warmup 20
%   [score, anomaly] = mtdi.ewma(x, alpha, threshold, warmup)
%   Same algorithm as mtdi.ml.EWMA (Python) and the C++, Java and JS SDKs; anomalies do
%   not update the reference. tests/test_sdks.py checks the numbers agree.
if nargin < 2, alpha = 0.05; end
if nargin < 3, threshold = 3.0; end
if nargin < 4, warmup = 20; end
x = x(:)';
score = zeros(size(x)); anomaly = false(size(x));
m = x(1); v = 0;
for i = 2:numel(x)
    sd = sqrt(v);
    if sd == 0, s = 0; else, s = (x(i) - m) / sd; end
    a = i > warmup && abs(s) >= threshold;
    if ~a
        d = x(i) - m;
        m = m + alpha * d;
        v = (1 - alpha) * (v + alpha * d * d);
    end
    score(i) = s; anomaly(i) = a;
end
end

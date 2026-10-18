function [score, anomaly] = cusum(x, drift, threshold, warmup)
%MTDI.CUSUM Two-sided CUSUM change detection for a whole series.
%   [score, anomaly] = mtdi.cusum(x)                     drift 0.5, threshold 8, warmup 100
%   The first WARMUP samples set the reference mean and (population) standard deviation;
%   the sums restart after every alarm. Same algorithm as mtdi.ml.CUSUM (Python).
if nargin < 2, drift = 0.5; end
if nargin < 3, threshold = 8.0; end
if nargin < 4, warmup = 100; end
x = x(:)';
score = zeros(size(x)); anomaly = false(size(x));
if numel(x) < warmup, return; end
ref = x(1:warmup);
m = mean(ref); sd = sqrt(mean((ref - m).^2));
if sd == 0, sd = 1e-12; end
pos = 0; neg = 0;
for i = warmup + 1:numel(x)
    z = (x(i) - m) / sd;
    pos = max(0, pos + z - drift);
    neg = max(0, neg - z - drift);
    score(i) = max(pos, neg);
    anomaly(i) = pos >= threshold || neg >= threshold;
    if anomaly(i), pos = 0; neg = 0; end
end
end

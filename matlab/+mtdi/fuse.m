function [value, variance] = fuse(values, variances)
%MTDI.FUSE Inverse-variance fusion of independent readings of one quantity.
%   [value, variance] = mtdi.fuse([10 20], [1 4])
%   Same as mtdi.fusion.fuse (Python). The fused variance is never larger than the best
%   sensor's. Every variance must be finite and > 0 (use the sensor's sigma squared).
values = values(:)'; variances = variances(:)';
if isempty(values) || numel(values) ~= numel(variances)
    error('mtdi:fuse', 'need one variance per reading');
end
if any(~isfinite(values)) || any(~isfinite(variances)) || any(variances <= 0)
    error('mtdi:fuse', 'readings must be finite and every variance finite and > 0');
end
scale = min(variances);                % relative weights: 1/variance overflows for tiny variances
w = scale ./ variances;
total = sum(w);
value = sum((values ./ total) .* w);
variance = max(scale / total, realmin * eps);   % never 0: the result must stay a valid input
end

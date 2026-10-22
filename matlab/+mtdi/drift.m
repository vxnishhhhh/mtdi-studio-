function s = drift(residuals, residualSd)
%MTDI.DRIFT Calibration spot checks (reference - calibrated reading) against the fit's promise.
%   s = mtdi.drift([0.1 -0.2 0.3], 0.5)
%   Same rule as mtdi.fusion.drift_summary (Python): drift needs at least 3 checks with an RMS
%   error above 3 x residualSd. With no residualSd (empty) drift is unknown: s.drift = [].
r = residuals(isfinite(residuals)); r = r(:)';
s = struct('checks', numel(r), 'rms', [], 'bias', [], 'limit', [], 'drift', []);
if isempty(r), return; end
scale = max(abs(r));                         % RMS without squaring overflow
if scale == 0
    s.rms = 0; s.bias = 0;
else
    s.rms = scale * sqrt(mean((r / scale) .^ 2));
    s.bias = scale * mean(r / scale);
end
if nargin >= 2 && ~isempty(residualSd)
    s.limit = 3 * residualSd;
    if numel(r) >= 3, s.drift = s.rms > s.limit; end
end
end

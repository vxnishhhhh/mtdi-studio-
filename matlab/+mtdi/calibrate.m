function cal = calibrate(raw, reference, temperature, tempRef)
%MTDI.CALIBRATE Fit true = gain*raw + offset (+ tempCoeff*(T - tempRef)) by least squares.
%   cal = mtdi.calibrate(raw, reference)                 offset and gain
%   cal = mtdi.calibrate(raw, reference, T)              plus temperature, tempRef 25
%   cal = mtdi.calibrate(raw, reference, T, tempRef)
%   Returns a struct with the same fields as mtdi.fusion.Calibration.to_dict (Python), so
%   jsonencode(cal) is a calibration file a project manifest can point at. Apply it with
%   mtdi.applyCalibration. Centring first keeps the fit well conditioned at any scale.
if nargin < 4, tempRef = 25; end
x = raw(:); y = reference(:);
if numel(x) ~= numel(y) || numel(x) < 3
    error('mtdi:calibrate', 'need at least 3 paired readings of equal length');
end
xc = x - mean(x); yc = y - mean(y);
sxx = sum(xc .^ 2);
if nargin < 3 || isempty(temperature)
    if sxx == 0, error('mtdi:calibrate', 'raw readings do not vary; cannot fit a gain'); end
    gain = sum(xc .* yc) / sxx;
    offset = mean(y) - gain * mean(x);
    cal = struct('gain', gain, 'offset', offset, 'temp_coeff', 0, 'temp_ref', tempRef, ...
                 'residual_sd', [], 'method', 'least-squares', 'n', numel(x));
    t = zeros(size(x));
else
    t = temperature(:) - tempRef;
    if numel(t) ~= numel(x), error('mtdi:calibrate', 'temperature must pair with every reading'); end
    tc = t - mean(t);
    stt = sum(tc .^ 2); sxt = sum(xc .* tc); det = sxx * stt - sxt ^ 2;
    if sxx == 0 || stt == 0 || det <= 1e-12 * sxx * stt
        error('mtdi:calibrate', 'raw readings and temperature are collinear; vary them independently');
    end
    sxy = sum(xc .* yc); sty = sum(tc .* yc);
    gain = (sxy * stt - sty * sxt) / det;
    coeff = (sty * sxx - sxy * sxt) / det;
    offset = mean(y) - gain * mean(x) - coeff * mean(t);
    cal = struct('gain', gain, 'offset', offset, 'temp_coeff', coeff, 'temp_ref', tempRef, ...
                 'residual_sd', [], 'method', 'least-squares+temperature', 'n', numel(x));
end
r = y - (cal.gain * x + cal.offset + cal.temp_coeff * t);
cal.residual_sd = sqrt(sum(r .^ 2) / max(1, numel(r) - 2));
end

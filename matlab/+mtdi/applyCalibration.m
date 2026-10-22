function value = applyCalibration(cal, raw, temperature)
%MTDI.APPLYCALIBRATION true = gain*raw + offset + temp_coeff*(T - temp_ref).
%   value = mtdi.applyCalibration(cal, raw)        no temperature term
%   value = mtdi.applyCalibration(cal, raw, T)
%   cal is a struct from mtdi.calibrate, or jsondecode of a saved calibration file.
value = cal.gain * raw + cal.offset;
if nargin >= 3 && ~isempty(temperature) && cal.temp_coeff ~= 0
    value = value + cal.temp_coeff * (temperature - cal.temp_ref);
end
end

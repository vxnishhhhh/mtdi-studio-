% CALIBRATE_SENSOR  Fit a sensor against a reference, save it, and check the fit.
%   Run from the repository root:  octave matlab/examples/calibrate_sensor.m   (or MATLAB's Run)
%   GUIDE: swap the simulated raw/reference/temperature for your logged readings.
addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
rand('seed', 1); randn('seed', 1);               % same numbers every run (Octave and MATLAB)

% Simulated sensor whose calibration should come out as: true = 1.7*raw - 2.3 + 0.04*(T - 25).
truth = linspace(0, 50, 40)';
temp  = 15 + 20 * rand(40, 1);
raw   = (truth + 2.3 - 0.04 * (temp - 25)) / 1.7 + 0.1 * randn(40, 1);

plain = mtdi.calibrate(raw, truth);
withT = mtdi.calibrate(raw, truth, temp, 25, 'TEMP');
fprintf('offset+gain:          gain %.3f  offset %+.3f  residual sd %.3f\n', plain.gain, plain.offset, plain.residual_sd);
fprintf('plus temperature:     gain %.3f  offset %+.3f  per C %+.4f  residual sd %.3f\n', ...
        withT.gain, withT.offset, withT.temp_coeff, withT.residual_sd);

% Saved as JSON, a project manifest can point a channel at it: "calibration": "co.cal.json".
out = fullfile(tempdir, 'co.cal.json');
fid = fopen(out, 'w'); fprintf(fid, '%s', jsonencode(withT)); fclose(fid);
fprintf('saved %s\n', out);

assert(withT.residual_sd < plain.residual_sd, 'the temperature term should help on this data');
fprintf('OK calibrate_sensor\n');

% DRIFT_CHECK  Spot-check a calibrated sensor against a reference until drift is decided.
%   Run from the repository root:  octave matlab/examples/drift_check.m
%   A sensor's own readings cannot reveal drift; only a reference can (see docs/MANIFEST.md).
addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
residualSd = 0.3;                                % from mtdi.calibrate at fit time

fresh = mtdi.drift([0.1 -0.2 0.25], residualSd);
fprintf('just calibrated: RMS %.3f, limit %.3f, drift %d\n', fresh.rms, fresh.limit, fresh.drift);
assert(~fresh.drift);

aged = mtdi.drift([1.1 1.3 0.9 1.2], residualSd);
fprintf('months later:    RMS %.3f, limit %.3f, drift %d (bias %+.2f: recalibrate)\n', ...
        aged.rms, aged.limit, aged.drift, aged.bias);
assert(aged.drift);

unknown = mtdi.drift([0.1 0.2 0.3], []);
assert(isempty(unknown.drift), 'no residual on file: drift cannot be judged');
fprintf('OK drift_check\n');

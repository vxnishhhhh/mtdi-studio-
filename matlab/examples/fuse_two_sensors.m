% FUSE_TWO_SENSORS  Two sensors, one quantity: the fused reading beats the better sensor.
%   Run from the repository root:  octave matlab/examples/fuse_two_sensors.m
addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
randn('seed', 2);

truth = 21.0;                                    % e.g. degrees C
sdA = 0.5; sdB = 1.2;                            % each sensor's measured noise
n = 2000; fused = zeros(n, 1); fusedSd = 0;
for k = 1:n
    a = truth + sdA * randn; b = truth + sdB * randn;
    [fused(k), v] = mtdi.fuse([a b], [sdA^2 sdB^2]);
    fusedSd = sqrt(v);
end
fprintf('sensor A sd %.3f, sensor B sd %.3f, fused sd %.3f (predicted), %.3f (observed)\n', ...
        sdA, sdB, fusedSd, std(fused));
assert(fusedSd < sdA, 'fusion must beat the better sensor');
assert(abs(std(fused) - fusedSd) < 0.05, 'observed spread should match the prediction');
fprintf('OK fuse_two_sensors\n');

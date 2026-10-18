function ok = verify(recordingFile, manifestFile, pythonJsonFile, tolerance)
%MTDI.VERIFY  Two implementations, one capture: compare MATLAB with Python.
%   Run `python -m mtdi analyze <project> <recording> > py.json` first, then
%   ok = mtdi.verify('session.jsonl', 'projects/x/project.json', 'py.json')
    if nargin < 4, tolerance = 1e-9; end
    m = mtdi.analyze(recordingFile, manifestFile);
    py = jsondecode(fileread(pythonJsonFile));
    ok = true;
    fields = {'samples', 'mean', 'median', 'noise', 'lod', 'loq', 'rate', 'clipped_share'};
    names = fieldnames(py);
    for k = 1:numel(names)
        for f = 1:numel(fields)
            if ~isfield(py.(names{k}), fields{f}), continue; end
            a = m.(names{k}).(fields{f}); b = py.(names{k}).(fields{f});
            if abs(a - b) > tolerance * max(1, abs(b))
                fprintf('MISMATCH %s.%s: MATLAB %.12g vs Python %.12g\n', names{k}, fields{f}, a, b);
                ok = false;
            end
        end
    end
    if ok, fprintf('MATLAB and Python agree on every channel.\n'); end
end

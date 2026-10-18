function rows = recording(file)
%MTDI.RECORDING  Read a JSONL session written by `python -m mtdi run ... --record FILE`.
%   rows is a cell array of structs with fields t, source, values, data_source.
    text = fileread(file);
    lines = regexp(text, '\r?\n', 'split');
    lines = lines(~cellfun(@(s) isempty(strtrim(s)), lines));
    rows = cellfun(@jsondecode, lines, 'UniformOutput', false);
end

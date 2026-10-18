function out = analyze(recordingFile, manifestFile)
%MTDI.ANALYZE  Independent MATLAB implementation of mtdi/analysis.py.
%   out = mtdi.analyze('session.jsonl', 'projects/x/project.json') returns a struct with one
%   field per channel: samples, mean, median, noise (1.4826*MAD), lod (3 sigma), loq (10 sigma),
%   rate, clipped_share, unit. It must agree with `python -m mtdi analyze` on the same files;
%   mtdi.verify checks that. Base MATLAB only (R2016b+ for jsondecode), no toolboxes.
    rows = mtdi.recording(recordingFile);
    manifest = jsondecode(fileread(manifestFile));
    channels = manifest.channels;
    if ~iscell(channels), channels = num2cell(channels); end
    out = struct();
    for c = 1:numel(channels)
        ch = channels{c};
        keys = cellstr(ch.keys);
        % jsondecode renames keys that are not valid identifiers (e.g. _SEQ, DIST-CM); look them up the same way.
        fkeys = matlab.lang.makeValidName(keys);
        sources = mtdi.sourcesOf(ch, manifest);
        n = numel(rows); mags = nan(n, 1); t = nan(n, 1); clipped = false(n, 1); used = false(n, 1);
        for r = 1:n
            row = rows{r};
            if ~any(strcmp(row.source, sources)), continue; end
            if ~all(isfield(row.values, fkeys)), continue; end
            raw = reshape(cellfun(@(k) double(row.values.(k)), fkeys), 1, []);   % row, whatever shape jsondecode gave
            if isfield(ch, 'raw_range') && ~isempty(ch.raw_range)
                clipped(r) = any(raw <= ch.raw_range(1) | raw >= ch.raw_range(2));
            end
            phys = raw .* mtdi.perKey(ch, 'scale', 1, numel(keys)) + mtdi.perKey(ch, 'offset', 0, numel(keys));
            if numel(phys) > 1, mags(r) = sqrt(sum(phys .^ 2)); else, mags(r) = phys; end
            t(r) = row.t; used(r) = true;
        end
        m = mags(used); tt = t(used); id = matlab.lang.makeValidName(ch.id);
        if isempty(m), out.(id) = struct('samples', 0); continue; end
        med = median(m);
        noise = 1.4826 * median(abs(m - med));
        span = 0; if numel(tt) > 1, span = tt(end) - tt(1); end
        rate = 0; if span > 0, rate = (numel(m) - 1) / span; end
        unit = ''; if isfield(ch, 'unit'), unit = ch.unit; end
        out.(id) = struct('samples', numel(m), 'mean', mean(m), 'median', med, 'noise', noise, ...
            'lod', 3 * noise, 'loq', 10 * noise, 'rate', rate, ...
            'clipped_share', sum(clipped(used)) / numel(m), 'unit', unit);
    end
end

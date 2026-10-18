function sources = sourcesOf(ch, manifest)
%MTDI.SOURCESOF  The source ids a channel accepts (default: the first declared source).
    if isfield(ch, 'source') && ~isempty(ch.source)
        sources = cellstr(ch.source);
    else
        s = manifest.sources; if iscell(s), s = s{1}; else, s = s(1); end
        sources = {s.id};
    end
end

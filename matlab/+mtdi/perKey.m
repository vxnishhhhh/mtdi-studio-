function v = perKey(ch, field, default, n)
%MTDI.PERKEY  A channel's scale or offset as a row vector of length n.
    if isfield(ch, field) && ~isempty(ch.(field)), v = double(ch.(field)(:)'); else, v = default; end
    if isscalar(v), v = repmat(v, 1, n); end
end

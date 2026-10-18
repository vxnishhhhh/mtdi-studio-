function p = packet(baseUrl)
%MTDI.PACKET  Read the live MTDI packet from a running studio.
%   p = mtdi.packet('http://localhost:8050') returns the same JSON the
%   interface draws: channels, fusion (score, condition, interpretation), sources.
    if nargin < 1, baseUrl = 'http://127.0.0.1:8050'; end
    p = webread([regexprep(baseUrl, '/+$', '') '/mtdi/packet'], weboptions('Timeout', 5));
end

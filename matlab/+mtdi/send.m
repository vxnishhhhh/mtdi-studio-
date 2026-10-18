function reply = send(url, token, sample)
%MTDI.SEND Push one sample into an MTDI studio (POST /api/ingest).
%   mtdi.send('https://my-studio.vercel.app', getenv('STUDIO_INGEST_TOKEN'), struct('ch2', 3.1))
%   ch1: a number or [x y z]   ch2: a number   ch3: struct('x', [...], 'y', [...])
opts = weboptions('MediaType', 'application/json', 'Timeout', 15);
if ~isempty(token)
    opts.HeaderFields = {'Authorization', ['Bearer ' token]};
end
reply = webwrite([regexprep(url, '/+$', '') '/api/ingest'], sample, opts);
end

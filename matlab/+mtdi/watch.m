function watch(baseUrl, seconds)
%MTDI.WATCH  Plot the MTDI score and every channel's deviation live from a running studio.
%   mtdi.watch('http://127.0.0.1:8050', 60)
    if nargin < 1, baseUrl = 'http://127.0.0.1:8050'; end
    if nargin < 2, seconds = 60; end
    figure('Name', 'MTDI live', 'Color', 'w');
    t0 = tic; T = []; S = [];
    while toc(t0) < seconds
        p = mtdi.packet(baseUrl);
        T(end + 1) = toc(t0); S(end + 1) = p.fusion.score; %#ok<AGROW>
        subplot(2, 1, 1); plot(T, S, 'LineWidth', 1.5); ylim([0 100]); ylabel('MTDI %');
        title(sprintf('%s · %s', p.project.name, p.fusion.condition), 'Interpreter', 'none');
        subplot(2, 1, 2); cla; hold on;
        names = fieldnames(p.channels);
        for k = 1:numel(names)
            c = p.channels.(names{k});
            if isfield(c, 'spark') && ~isempty(c.spark), plot(c.spark, 'DisplayName', c.label); end
        end
        hold off; legend('show', 'Location', 'eastoutside'); ylabel('deviation');
        drawnow; pause(1);
    end
end

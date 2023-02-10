% include('header.tpl', title='Config File')

<br />
<div style="font-family: monospace, monospace;">
python3 splunk_export_parallel.py 
%for k,v in rows.items():
%   exclude_list=['generate-format','data_output']
%   if k not in exclude_list:
%       if len(v) > 0:
            --{{k}} "{{v}}"
        %end
    %end
%end
</div>

% include('footer.tpl')
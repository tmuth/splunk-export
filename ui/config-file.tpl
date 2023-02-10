% include('ui/header.tpl', title='Config File')

<div style="font-family: monospace;">

%for k,v in rows.items():
%   exclude_list=['generate-format','data_output']
%   if k not in exclude_list:
%       if len(v) > 0:
            {{k}}={{v}} <br />
        %end
    %end
%end



</div>

<%
  #  name='foo'.upper()
%>
%#{{name}}
% include('ui/footer.tpl')
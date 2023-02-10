% include('header.tpl', title='Parameters Output')
<p>{{status}}</p>
SPLUNK_HOST: {{payload['SPLUNK_HOST']}}<br />
SPLUNK_PORT: {{payload['SPLUNK_PORT']}}<br />
SPLUNK_AUTH_TOKEN: {{payload['SPLUNK_AUTH_TOKEN']}}<br />
%if rows:
Server Name: {{rows.serverName}}<br />
OS Name: {{rows.os_name}}<br />
Number of Cores: {{rows.numberOfCores}}<br />
Number of Virtual Cores: {{rows.numberOfVirtualCores}} <br />


<div style="overflow-y:auto; height:400px; width:600px;">
<table border="1">
%for k,v in rows.items():
  <tr>
    <td>{{k}}</td><td>{{v}}</td>
  </tr>
%end
</table>
</div>
%end
% include('footer.tpl')
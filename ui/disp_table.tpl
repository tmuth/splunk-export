% include('ui/header.tpl', title='Parameters Output')
<p>The items are as follows:</p>
<table border="1">
%for k,v in rows.items():
  <tr>
    <td>{{k}}</td><td>{{v}}</td>
  </tr>
%end
</table>
% include('ui/footer.tpl')
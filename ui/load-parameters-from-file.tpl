% include('ui/header.tpl', title='Load Parameters from File')

<form method='post' action='/process-uploaded-parameters' enctype='multipart/form-data'>
    Parameter File: <input type='file' name='parameterFile' />
   
    <input type='submit' value='Upload' />
</form>

<%
  #  name='foo'.upper()
%>
%#{{name}}
% include('ui/footer.tpl')
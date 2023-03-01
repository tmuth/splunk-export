% include('ui/header.tpl', title='Run Interactively')
% import subprocess,urllib.parse

<br />
<div style="font-family: monospace, monospace;">
python3 splunk_export_parallel.py 
%parameters_string=''
%for k,v in rows.items():
%   
%   exclude_list=['generate-format','data_output']
%   if k not in exclude_list:
%       if len(v) > 0:
%           parameters_string += '--'+k+' "'+v+'" '
            --{{k}} "{{v}}"
        %end
    %end
%end
% parameters_string = urllib.parse.quote(parameters_string.encode('utf8'))
</div>
<form action="" method="post" id="parameterform">
    <input type="hidden" name="parameters" id="runParameters" value="{{parameters_string}}" />
    

</form>
<input value="Run Export" id="runButton" type="submit" />

<div id="progressbar" style="width:300px;"><div class="progress-label">Loading...</div></div>

<div id="progress-output" title="" style="display:block; border:1px #aaaaaa solid;">
</div>
<div id="server-info" title="" class="script-output row">
</div>
<div id="script-output" title=""  class="script-output">
</div>


<script>
    function runScriptInline() {
        $.ajaxSetup({
            data: {
                RUN_PARAMETERS: $('input[name="parameters"]').val()
            }
        });

        $.ajax({
            // url: '/run-script',
            url: '/stream',
            type: "POST",
            success: function (data) {
                // $("#dialog-message").load(data).dialog({modal:true}).dialog('open');
                $("#dialog-message").html(script-output)
                
            }
        });
    } 

    $("#runButton").click(function () {
        console.log('run button clicked')
        $( "#progressbar" ).progressbar( "value", 0 );
        $( "#progressbar" ).show()
        $("#script-output").html('');
        $("#server-info").html('');
        str=' --log_format "json"'
        var encoded = encodeURIComponent(str);
        var es = new EventSource("/stream?parameters="+$('#runParameters').val()+encoded);
        // var es = new EventSource();

        es.addEventListener("end_session", (e) => {
            // console.log(e.data);
            var data = JSON.parse(e.data);
            // console.log(data.message);
            console.log("Closing SSE Session");
            es.close();
        });

        es.addEventListener("log", (e) => {
            console.log(e.data);
            var data = JSON.parse(e.data);
            // console.log(data.message);
            if(data.name == "progress") {
                $("#progress-output").html(data.message+'<br />');

                $( "#progressbar" ).progressbar( "value", parseInt(data.message) );
            }
            else if(data.name == "UI") {
                console.log(data.message)
                if(data.component=="progress"){
                    // $("#progress-output").html(data.message+'<br />');
                    $( "#progressbar" ).progressbar( "value", parseInt(data.message) );
                }
                else if(data.component=="server_info") {
                    // tr = str.replace(/\'/g, '"');
                    // var info = JSON.parse(data.message);
                    $("#server-info").append('<div class="columnTitle">'+data.message.key+': </div> <div class="column">'+data.message.value+'</div>');
                }

            }
            else{
                $("#script-output").append(data.message+'<br />');
            }
        });


        es.onmessage = function(e) {
            // document.getElementById("log").innerHTML = e.data;
            console.log(e)
            // const data = JSON.parse(e.data)
            // console.log(type)
            // console.log(data)
            // if (e.id == "CLOSE") {
            if (e.data == "") {
                console.log("Closing EventSource")
                es.close(); 
            }
            else {
                $("#script-output").append(e.data+'<br />');
            }
            
        }

        
        //  runScriptInline()
    })

    // $( "#progressbar" ).progressbar({
    //   value: 0
    // });

    $( function() {
        var progressbar = $( "#progressbar" ),
        progressLabel = $( ".progress-label" );
        $( "#progressbar" ).hide()
    
        progressbar.progressbar({
        value: false,
        change: function() {
            progressLabel.text( progressbar.progressbar( "value" ) + "%" );
        },
        complete: function() {
            progressLabel.text( "Complete!" );
        }
        });
    } );


</script>

% include('ui/footer.tpl')
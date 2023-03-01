% include('ui/header.tpl', title='Parameters')
<h1>Splunk Export Parameter Generator</h1>
<h2>Version:  20230228_215453</h2>
<form action="/parametergen" method="post" id="parameterform">

    <fieldset>
        <legend data-title="MAIN_OPTIONS">Main Options</legend>

        <label>Parameter Format:</label><select name="generate-format">
            <option disabled selected value> -- select an option -- </option>
            <option>command-line</option>
            <option>config-file</option>
            <option>run-interactively</option>
            <option>display_table</option>
        </select>

        <label>Data Destination:</label>
        <label for="filesOutput">Files
            <input type="radio" id="filesOutput" name="data_output" value="Files" checked="checked" />
        </label>

        <label for="hecOutput">HEC<input type="radio" id="hecOutput" name="data_output" value="HEC" /></label>
        <div>
            <label>Log Level:</label><select name="log_level">
                <option>DEBUG</option>
                <option selected value="INFO">INFO</option>
                <option>WARNING</option>
                <option>ERROR</option>
                <option>CRITICAL</option>
            </select>
        </div>
    </fieldset>



    <fieldset>
        <legend data-title="JOB">Job</legend>
        <!-- <div class="controlgroup"></div> -->
        <label for="jobName">Job Name:</label> <input id="jobName" name="job_name" type="text" class="inputTextMedium" minlength="2" required
            title="A directory with this name will be created to contain the catalog metadata files, not the actual export data files." />
        <label for="jobLocation" >Job Location:</label> <input name="job_location" id="jobLocation" type="text" value="../" class="inputTextLong"
            title="Path to store the catalog for this job" />

        <!-- </div> -->
    </fieldset>

    <fieldset>
        <legend data-title="SPLUNK">Splunk</legend>
        <!-- <div class="controlgroup"></div> -->
        <label for="splunkHost">SPLUNK_HOST:</label> <input id="splunkHost" name="SPLUNK_HOST" type="text" class="inputTextMedium"
            title="The hostname that contains the source data" minlength="2" required />
        <label for="splunkPort">SPLUNK_PORT:</label> <input name="SPLUNK_PORT" id="splunkPort" type="text" class="inputNumber" value="8000" minlength="2" required />
        <div><label for="splunkAuthToken" >SPLUNK_AUTH_TOKEN:</label> <input name="SPLUNK_AUTH_TOKEN" id="splunkAuthToken" type="text" class="inputTextLong" minlength="2" required 
                title="Authentication token to use in place of a username/password combination. This is not the same as a HEC token. Pass it in directly or set an environment variable and pass in the name of the environment variable enclosed %. For example %DEV_TOKEN%" />
            <a class="ui-button ui-widget ui-corner-all" href="#" id="splunkTestButton">Test Splunk Connection</a>
        </div>

        <!-- </div> -->
    </fieldset>

    <fieldset id="fileFormatFieldset">
        <legend data-title="FILE_OUTPUT_FORMAT">File Data Output Format</legend>
        <!-- <div class="controlgroup"></div> -->
        <label>Output Format:</label><select name="output_format">
            <option selected value>json</option>
            <option>csv</option>
            <option>raw</option>
        </select>

        <label>GZIP Files</label>
        <input type="radio" id="gzipFileFalse" name="gzip" value="False" checked="checked" />
        <label for="filesOutput">False</label>
        <input type="radio" id="gzipFileTrue" name="gzip" value="True" />
        <label for="gzipFileTrue">True</label>
        <label>Max File Size MB:</label> <input name="max_file_size_mb" type="text" value="0" class="inputNumber"
            title="The approximate maximum size in megabytes of each export file. 0 for unlimited" />

        <!-- </div> -->

    </fieldset>

    <fieldset id="fileOutputFieldset">
        <legend data-title="FILE_OUTPUT">File Data Output</legend>
        <!-- <div class="controlgroup"></div> -->
        <label>DIRECTORY:</label> <input name="directory" type="text" value="../" class="inputTextLong"
            title="Relative or absolute path to output data files" />
        <!-- </div> -->
    </fieldset>


    <fieldset id="hecOutputFieldset">
        <legend data-title="HEC">HEC Data Output</legend>
        <!-- <div class="controlgroup"></div> -->
        <label>HEC_HOST:</label> <input name="HEC_HOST" type="text" />
        <label>HEC_PORT:</label> <input name="HEC_PORT" type="text" value="8089" />
        <label>HEC_TOKEN:</label> <input name="HEC_TOKEN" type="text" class="inputTextLong" /><br />
        <label>HEC_TLS:</label><select name="HEC_TLS">
            <option>True</option>
            <option selected>False</option>
        </select>
        <label>HEC_TLS_VERIFY:</label><select name="HEC_TLS_VERIFY">
            <option>True</option>
            <option selected>False</option>
        </select><br />
        <!-- </div> -->
    </fieldset>
    <fieldset>
        <legend data-title="SEARCH">Search</legend>
        <!-- <div class="controlgroup"> -->
            <label for="indexesInput">INDEXES:</label> <input name="indexes" id="indexesInput" type="text" class="inputTextMedium" minlength="2" required 
                title="A comma separated list of indexes to export. This cannot be null or *" />
            <label for="sourcesInput">SOURCETYPES:</label> <input name="sourcetypes" id="sourcesInput" type="text" class="inputTextMedium" value="*"
                title="A comma separated list of sourcetypes to export. " />
            <br />
            <label for="beginDate">BEGIN_DATE:</label> <input name="begin_date" id="beginDate" type="text" minlength="2" required />
            <label for="endDate" >END_DATE:</label> <input name="end_date" id="endDate" type="text" minlength="2" required /> <br />
            <label for="extraSearch">EXTRA:</label> <input name="extra" id="extraSearch" type="text" class="inputTextLong" value="| table *"
                title="Post-search formatting commands in SPL format. The utility will construct the filter part of the search using the indexes, sourcetypes, date range and partition intervals. The 'EXTRA' attribute is then appended to each of these searches. For example '| head 100 | table *' ' " />
            <br />
            <label>Sample Ratio:</label> <input name="sample_ratio" type="text" class="inputNumber" value="0"
                title="The integer value used to calculate the sample ratio. The formula is 1 / [integer]." />
        <!-- </div> -->
    </fieldset>
    <fieldset id="exportFieldset">
        <legend data-title="EXPORT">Export</legend>
        <!-- <div class="controlgroup"> -->
        <label for="parallelProcesses">Parallel Processes:</label> <input name="parallel_processes" id="parallelProcesses" type="text" class="inputNumber" value="1" minlength="1" required 
            title="The number of concurrent processes to run for this export. This should be less than the number of CPU cores on the Search Head and not more than the number of partitions. Note that the export has to be partitioned to execute using more than one worker. For instance, if you are only exporting 1 index/sourcetype for 1 day, perhaps partition by '1 hours' is a good start." /> <br />
        
        <label for="paritionUnits">Partition Units:</label><select name="parition_units" id="paritionUnits">
            <option value="days" selected>days</option>
            <option value="hours">hours</option>
        </select>
        <label for="paritionInterval">Partition Interval:</label> <input name="partition_interval" id="paritionInterval" type="text" class="inputNumber" value="1" minlength="1" required 
            title="Combines with Partition Units to determine how to divide the export by time." /> <br />
        <label for="resumeMode">Resume Mode:</label><select name="resume_mode" id="resumeMode" title="If the previous run failed, start where it left off.">
            <option>resume</option>
            <option selected>overwrite</option>
        </select><br />
        <label for="incrementalMode" >Incremental Mode:</label><select name="incremental_mode" id="incrementalMode" title="Incremental mode keeps track of the last exported date by index and sourcetype of the previous run, then uses that date as the earliest date in the searches for the current run">
            <option>True</option>
            <option selected>False</option>
        </select>
        <label for="incrementalTimeSource" >Incremental Time Source:</label><select name="incremental_time_source" id="incrementalTimeSource" title="Determines if the last export dates are tracked by files in the catalog or by running searches against the destination">
            <option selected>search</option>
            <option>file</option>
        </select>

        <!-- </div> -->
    </fieldset>
    
    <script>
        $(function () {
            $("input[name='begin_date']").datetimepicker({dateFormat: "yy-mm-dd"});
            $("input[name='end_date']").datetimepicker({dateFormat: "yy-mm-dd"});
        });
    </script>

    <br /><br />
    <input value="Generate" id="generateButton" type="submit" />
</form>

<div id="dialog-message" title="" style="display:none;">
</div>
<script>
    $(function () {
        $(".controlgroup").controlgroup()
        $(".controlgroup-vertical").controlgroup({
            "direction": "vertical"
        });
    });

    function setGenerateFormat() {
        var selected = $("select[name='generate-format']").children(":selected").text();
        $("#parameterform").attr('action', '/' + selected);
    }

    $("select[name='generate-format']").change(function () {
        //var selected = $(this).children(":selected").text();
        //console.log($(this).children(":selected").text());
        //$("#parameterform").attr('action', '/' + selected);
        setGenerateFormat()
    })

    $(function () {
        $(document).tooltip();
    });

    function saveValuesToCookie() {
        $("form#parameterform :input").not(':input[type=button], :input[type=submit], :input[type=reset]').each(function () {
            //$.each($("form").elements, function(){ 
            //console.log($(this).attr("name")+' - '+$(this).attr("value"));
            // console.log($(this));

            if ($(this).is(':radio')) {
                if ($(this).is(":checked")) { // check if the radio is checked
                    var val = $(this).val(); // retrieve the value
                    //console.log($(this).attr("name")+' - '+val);
                    if (val !== null) {
                        Cookies.set($(this).attr("name"), val, { expires: 90 });
                    }
                }
            }
            else {
                // console.log($(this).attr("name")+' - '+$(this).val());
                if ($(this).val() !== null) {
                    Cookies.set($(this).attr("name"), $(this).val(), { expires: 90 });
                }
            }
        });
    }

    function getValuesFromCookie() {
        $("form#parameterform :input").not(':input[type=button], :input[type=submit], :input[type=reset]').each(function () {
            //console.log($(this).attr("name")+' - '+$(this).attr("value"));
            // console.log($(this));

            if ($(this).is(':radio')) {
                inputName = $(this).attr("name")
                inputVale = Cookies.get(inputName);
                $('input:radio[name=' + inputName + ']').filter('[value=' + inputVale + ']').prop('checked', true);
            }
            else {
                str = Cookies.get($(this).attr("name"));
                if (str !== null) {
                    $(this).val(str)
                }
            }
            //your code here 
        });
    }
    function setFilesOrHec() {
        data_output_radio = $("input[name$='data_output']:checked");
        var test = $(data_output_radio).val();
        // console.log(test);
        if (test == "Files") {
            $('#fileOutputFieldset').show()
            $('#fileFormatFieldset').show()
            $('#hecOutputFieldset').hide()
        }
        else {
            $('#fileOutputFieldset').hide()
            $('#fileFormatFieldset').hide()
            $('#hecOutputFieldset').show()
        }
    }

    $(document).ready(function () {
        $('#hecOutputFieldset').hide()
        $("input[name$='data_output']").click(function () {
            setFilesOrHec();
            // var test = $(this).val();
            // if (test == "Files") {
            //     $('#fileOutputFieldset').show()
            //     $('#fileFormatFieldset').show()
            //     $('#hecOutputFieldset').hide()
            // }
            // else {
            //     $('#fileOutputFieldset').hide()
            //     $('#fileFormatFieldset').hide()
            //     $('#hecOutputFieldset').show()
            // }
        });


        getValuesFromCookie()
        setGenerateFormat()
        setFilesOrHec();

        $("#generateButton").click(function () {
            saveValuesToCookie()
        })

        $("#splunkTestButton").click(function () {
            showUrlInDialog()
        })
        // Future: implement fieldset grouping with:
        //$('fieldset').each(function(){
        //console.log($(this).find('legend').text())
        //console.log($(this).find('legend').attr("data-title"))
        //})
    })

    function openTestDialog() {
        $("#dialog-message").dialog({
            modal: true,
            buttons: {
                Ok: function () {
                    $(this).dialog("close");
                }
            }
        });
    }

    function showUrlInDialog() {
        $.ajaxSetup({
            data: {
                SPLUNK_HOST: $('input[name="SPLUNK_HOST"]').val(),
                SPLUNK_PORT: $('input[name="SPLUNK_PORT"]').val(),
                SPLUNK_AUTH_TOKEN: $('input[name="SPLUNK_AUTH_TOKEN"]').val()
            }
        });

        $.ajax({
            url: '/splunk-connect',
            type: "POST",
            success: function (data) {
                // $("#dialog-message").load(data).dialog({modal:true}).dialog('open');
                $("#dialog-message").html(data)
                $("#dialog-message").dialog({
                    autoOpen: false,
                    width: 600,
                    height: 500,
                    title: 'Splunk Connection Test'
                });
                $("#dialog-message").dialog({ modal: true }).dialog('open');
            }
        });
    } 

    $(function() {
  // Initialize form validation on the registration form.
  // It has the name attribute "registration"
        $("#parameterform").validate();
    
    });

    $('#parameterform').find(':input').filter('[required]').each(function(){
        $this = $(this);
        $label = $('label[for="'+ $this.attr('id') +'"]');

        if ($label.length > 0 ) {
            //this input has a label associated with it, lets do something!
            //$label.css({"color":"red"});
            var str ='<span>*</span>';
            $label.append(str);
            $label.find('span').css({"color":"red"});
        }
    });
</script>



% include('ui/footer.tpl')
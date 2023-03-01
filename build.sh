#!/bin/sh

version=`date '+%Y%m%d_%H%M%S'`
echo ${version} > version_number

replace_version() {
  local search_in=$1
  local replace_in=$2
  local file_in=$3

  sed -i "" "s/${search_in}/${replace_in}/g" ${file_in}
}


search="^\(__version__ =\).*"
replace="\1 \"${version}\""
replace_version "${search}" "${replace}"  "splunk_export_parallel.py"

search="^\(<h2>Version: \)\([[:digit:]_ ]\{1,\}\).*\(<\/h2>\)"
replace="\1 ${version}\3"
replace_version "${search}" "${replace}" "ui/parameters.tpl"

git commit splunk_export_parallel.py -m "$1"
git commit ui/parameters.tpl -m "$1"
git push origin main 
git tag ${version}
git push origin -f --tags
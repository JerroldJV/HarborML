# plumber.R
source('plumber/loader.R')

log_it <- function(call, input, output){
  cat(strftime(Sys.time(), "%Y-%m-%d %H:%M:%OS"))
  cat("\t|\t")
  cat(call)
  cat("\t|\t")
  cat(input)
  cat("\t|\t")
  cat(output)
  cat("\n")
}

#* Perform a model prediction
#* @param data Data passed down to predict function
#* @post /
function(data){
  result <- api_predict(data)
  log_it('predict', data, result)
  return(result)
}

#* Debug the prediction
#* @html
#* @get /debug
function(){
  log_it('debug_get', '', '')
  return('
  <html>
  <body>
  <form action=\'\' method=\'post\'>
      <textarea name="jsondata" cols="100" rows="20"></textarea><br/>
      <button>Test</button>
 </form>
 </body>
 </html>')
}

#* Debug the prediction
#* @param data Data passed down to predict function
#* @post /debug
function(jsondata){
  data <- jsonlite::fromJSON(jsondata)$data
  result <- api_predict(data)
  log_it('debug_post', data, result)
  return(result)
}

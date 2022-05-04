var http = require('http')
var server = http.createServer()
server.on('request', function (request, response) {
  response.write('<h1>Node 10.18.1: Smuggling Test.')
  response.end()
})

server.listen(8080)

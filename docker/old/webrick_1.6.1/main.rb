#!/usr/bin/env ruby
 
require  'webrick'
 
class Server < WEBrick::HTTPServlet::AbstractServlet
    def do_GET (request, response)
		response.body = 
          "<h1>Webrick 1.6.1: Smuggling Test.</h1>"
    end

    def do_POST (request, response)
		response.body = 
          "<h1>Webrick 1.6.1: Smuggling Test.</h1>"
    end
end

server = WEBrick::HTTPServer.new(:Port => 8080)

server.mount "/", Server

trap("INT") {
    server.shutdown
}

server.start

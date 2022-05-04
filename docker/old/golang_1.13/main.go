package main

import (
	"fmt"
	"net/http"
)

func IndexHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintln(w, "<h1>Golang 1.13: Smuggling Test.</h1>")
}

func main() {
	http.HandleFunc("/", IndexHandler)
	http.ListenAndServe("0.0.0.0:8080", nil)
}

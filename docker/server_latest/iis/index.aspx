<%@ Page Language="C#"%>
<%
    // string[] keys = Request.Form.AllKeys;
    // for (int i= 0; i < keys.Length; i++) {
    //     Response.Write(keys[i] + "=" + Request.Form[keys[i]] + "");
    // }
    string requestedDomain = HttpContext.Current.Request.ServerVariables["HTTP_HOST"];
    string requestedURI = HttpContext.Current.Request.Url.PathAndQuery;
    string json = "{\"URI\":\"" + requestedURI + "\",\"Host\":\"" + requestedDomain + "\"}";
    Response.Clear();
    Response.ContentType = "application/json; charset=utf-8";
    Response.Write(json);
    Response.End();
%>

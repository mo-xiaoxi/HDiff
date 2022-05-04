<?php
$host = $_SERVER['HTTP_HOST'];
if ($_SERVER['QUERY_STRING'] == "") {
    $path = $_SERVER['PHP_SELF'];
} else {
    $path = $_SERVER['PHP_SELF'].'?'.$_SERVER['QUERY_STRING'];
}

$input = file_get_contents('php://input');

$ret = array('URI' => $path, 'Host' => $host, 'input'=>$input);
$ret = json_encode($ret);
$ret = str_replace("\\/", "/", $ret);
echo $ret;

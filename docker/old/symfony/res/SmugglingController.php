<?php
namespace App\Controller;

use Symfony\Component\HttpFoundation\Response;

class SmugglingController
{
    public function smuggling(): Response
    {
        return new Response(
            '<h1>Symfony: Smuggling Test.</h1>'
        );
    }
}

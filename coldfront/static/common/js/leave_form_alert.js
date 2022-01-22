/**
 * If any form was modified, raise a warning before the user may leave.
 */

var submitted = false;
var firstPage = false;

$(document).ready(function() {
    var bodyText = document.body.textContent || document.body.innerText;
    if (bodyText.indexOf('Step 1 of') > -1) {
        firstPage = true;
    }

    $('form').each(function() {
        $(this).dirty({preventLeaving: true});
    });

    $("form").submit(function() {
        submitted = true;
    });

    window.onbeforeunload = function (e) {
        if (!firstPage && !submitted) {
            return true;
        }
    }
});

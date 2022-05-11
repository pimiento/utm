var changer = function () {
    var to_seconds = 200,
        height = $(window).height() - 10,
        width = $(window).width() - 10;

    $.get('/get', function(resp) {

        if (resp['type'] === 'photo') {
            $('#VIDEO').trigger('pause');
            $('#VIDEO').hide();
            $('#BLOCK').show();
            if (resp['height'] <= height)
                height = resp['height'];
            if (resp['width'] <= width)
                width = resp['width'];

            $('#BLOCK').css({
                'background-image': 'url(/static/' + resp['src'] + ')',
                'width': width,
                'height': height
            });
            window.setTimeout(changer, resp['pause'] * to_seconds);
        } else {
            var video = $('#VIDEO');
            $('#BLOCK').hide();
            video.attr('src', resp['src']);
            video.show();
            if (video.requestFullScreen) {
                video.requestFullScreen();
            } else if (video.mozRequestFullScreen) { /* Firefox */
                video.mozRequestFullScreen();
            } else if (video.webkitRequestFullscreen) { /* Chrome, Safari & Opera */
                video.webkitRequestFullscreen();
            } else if (video.msRequestFullscreen) { /* IE/Edge */
                video.msRequestFullscreen();
            }
            video.trigger('play');
            window.setTimeout(changer, resp['pause']*1000);
        }
    });
};

$(document).ready(function() {
    var response, timeout = 0,
        ws = new WebSocket('ws://localhost:8888/chat'),
        next = $('#next_orquesta'),
        chat = $('#chat'),
        nextTimeout, chatTimeout;
    next.hide();
    chat.hide();
    window.setTimeout(changer, timeout);
    // W3 — WWWW C - consorcium
    ws.onmessage = function (evt) {
        console.log(evt.data);
        var data = JSON.parse(evt.data);
        if (data['type'] === 'next') {
            clearTimeout(nextTimeout);
            if (!data['next']) {
                next.hide();
            }
            next.show();
            next.text(data['next']);
            nextTimeout = setTimeout(function () { next.hide(); }, data['duration']);
        } else if (data['type'] === 'message') {
            chat.show();
            chat.text(data['message']);
            chatTimeout = setTimeout(function () { chat.hide(); }, data['duration']);
        }
    };
});

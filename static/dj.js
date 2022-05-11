var intervalId,
    timeoutId,
    sec = 1000,
    minute = sec * 60,
    period = 5 * sec,
    duration = period * 60, my_ws;

JSON.stringify = JSON.stringify || function (obj) {
    var t = typeof (obj);
    if (t != "object" || obj === null) {
        // simple data type
        if (t == "string") obj = '"'+obj+'"';
        return String(obj);
    }
    else {
        // recurse array or object
        var n, v, json = [], arr = (obj && obj.constructor == Array);
        for (n in obj) {
            v = obj[n]; t = typeof(v);
            if (t == "string") v = '"'+v+'"';
            else if (t == "object" && v !== null) v = JSON.stringify(v);
            json.push((arr ? "" : '"' + n + '":') + String(v));
        }
        return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
    }
};

var increaseProgressBar = function (value) {
    var bar = $('PROGRESS');
    if (value >= 60) {
        progressTrigger(null, null, 'stop');
    } else {
        bar.val(value);
        intervalId = window.setTimeout(increaseProgressBar, period, value+1);
    }
};

var progressTrigger = function (msg, duration, action, cur) {
    var container = $('#TIMER'),
        box = $('#NEXT_ORQUESTA'),
        cur = (typeof cur === 'undefined') ? 0 : cur,
        action = (typeof action === 'undefined') ? 'start' : action;

    clearInterval(intervalId);
    if (action === 'stop') {
        container.hide();
    } else {
        if (cur === 0) {
            box.text('Далее: ' + msg);
            container.show();
        }
        increaseProgressBar(cur);
    }
};

var orquestaTrigger = function (elem, ws) {
    var activeClass = 'is-danger',
        inactiveClass = 'is-info',
        value = elem.attr('value'), result;
    my_ws = ws;

    clearTimeout(timeoutId);
    if (elem.hasClass(activeClass)) {
        ws.send(JSON.stringify({type: "next", next: null}));
        elem.removeClass(activeClass);
        elem.addClass(inactiveClass);
        progressTrigger(null, null, 'stop');
    } else if (value != '') {
        $('button').removeClass(activeClass).addClass(inactiveClass);
        progressTrigger(null, null, 'stop');
        result =JSON.stringify({
            type: "next",
            next: 'Далее: ' + value,
            duration: duration
        });
        ws.send(result);
        elem.addClass(activeClass);
        elem.removeClass(inactiveClass);
        progressTrigger(value, duration, 'start');
        timeoutId = window.setTimeout(orquestaTrigger, duration, elem, ws);
    }

};

var customOrquesta = function(ws) {
    var button = $('#CUSTOM_ORQUESTA'),
        input = $('#ORQUESTA'),
        value = input.val();
    input.attr("disabled", "disabled");
    button.attr('value', value);
    if (value != '') {
        input.val('');
        input.attr('placeholder', value);
    }
    input.removeAttr("disabled");
    orquestaTrigger(button, ws);
};

var sendMessage = function (ws) {
    var message = $('#CHAT').val();
    ws.send(JSON.stringify({type: "message", message: message, duration: minute * 3}));
    $('#CHAT').val('');
};

$(document).ready(function() {
    var ws = new WebSocket("ws://localhost:8888/chat");
    ws.onopen = function () {
        ws.send('{"init": "dj", "type": "conn"}');
    };
    $('#TIMER').hide();

    $('.orquesta').click(function () {
        orquestaTrigger($(this), ws);
    });
    $('#ORQUESTA').on('keypress', function (e) {
        if ((e.keyCode == 10 || e.keyCode == 13) && e.ctrlKey) { customOrquesta(ws); }
    });
    $('#CUSTOM_ORQUESTA').click(function () {
        customOrquesta(ws);
    });
    $('#CHAT').on('keypress', function (e) {
        if ((e.keyCode == 10 || e.keyCode == 13) && e.ctrlKey) { sendMessage(ws); }
    });
    $('#SEND_MESSAGE').click(function () {
        sendMessage(ws);
    });
});

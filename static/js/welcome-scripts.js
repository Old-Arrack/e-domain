/*!
* Start Bootstrap - One Page Wonder v6.0.4 (https://startbootstrap.com/theme/one-page-wonder)
* Copyright 2013-2021 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-one-page-wonder/blob/master/LICENSE)
*/
// This file is intentionally blank
// Use this file to add JavaScript to your project

function color(num) {
    for(var n=0; n<5; n++){
        var icon = document.getElementById(`I${n}`);
        icon.style.color = "inherit";
    }

    var hex_codes = ["red", "orange", "yellow", "#9AFF00", "#09B411"];
    var rate = document.getElementById("Rate");
    var current_icon = document.getElementById(`I${num}`);

    current_icon.style.color = hex_codes[num];
    rate.value = num;
}
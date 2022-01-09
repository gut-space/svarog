function clicked_img(img,fp){
    console.log(img.src);

    var top=document.getElementById('gallery-top')

    top.src = img.src;

    top.hidden=false;

    if (img.naturalWidth<screen.width*0.6 && img.naturalHeight<screen.height*0.6) {
        top.width=img.naturalWidth;
        top.height=img.naturalHeight;
    } else {
        top.width=screen.width*0.6;
        top.height=img.naturalHeight/img.naturalWidth*top.width;
    }

    document.getElementById('gallery-overlay').hidden = false;
    document.getElementById('gallery-descr').innerText = img.alt;
}

function do_close(){
    document.getElementById('gallery-overlay').hidden=true;
}
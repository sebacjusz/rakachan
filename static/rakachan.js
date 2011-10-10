
function ppv(t, board,id){
	$("<div id='preview' style='position: fixed'></div>").appendTo("body");
	$('#preview').load('/post/' + board + '/' + id);
	var position = $(t).position(); 
	$('#preview').css('top', parseInt(position.top) - window.pageYOffset); 
	i = parseInt(position.left) + parseInt($(t).css('width'));
	$('#preview').css('left', i);
}

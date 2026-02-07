if(navigator.serviceWorker){
	console.log('install Service work');
        navigator.serviceWorker.register('/OneSignalSDKWorker.js?v=5')
		.then(function (registration){
			console.log(registration);
		}).catch(function (e) {  
			console.error(e);
		});
}else{
    console.log('Service Worker is not supported in this browser.');
}
/*
setInterval(function(){
	if (!navigator.onLine) {
		window.location.href = '/offline.html';
	} 
}, 20000); 
*/
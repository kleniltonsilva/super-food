let serviceHours = null;
let serviceHoursToday = null;
let htmlServiceHoursToday = "";
let intervalNotificationPauseDeliveryOnline = null;
const pauseDeliveryOnline = {
  status: false,
  time: 0,
  date: null
}

$(document).ready(function(){
  Cookies.remove("itemInEditingED");
  setAddress();
  checkRedirectCombo();
  renderServiceHoursToday();

  const pauseDeliveryOnlineData = JSON.parse($("#pauseDeliveryOnline").val());
  pauseDeliveryOnline["status"] = pauseDeliveryOnlineData["status"];
  pauseDeliveryOnline["time"] = pauseDeliveryOnlineData["time"];
  pauseDeliveryOnline["date"] = pauseDeliveryOnlineData["date"];
  
  $(document).on('click', '.linkModalServiceHours', function(){
    openModalServiceHours();
  });

  const urlParams = new URLSearchParams(window.location.search);
  const campaignId = urlParams.get('campaign');
  if (campaignId) {
    Cookies.set('trackerED_campaignId', campaignId);
  }

  if (isDesktopEddy) {
    showNotificationPauseDeliveryOnline();
    showNotificationAroundClosingTime();
  }

  if (isMobile) {
    const pathname = window.location.pathname;
    if (pathname == "/cardapio/" || pathname == "/") {
      showNotificationPauseDeliveryOnline();
      showNotificationAroundClosingTime();
    }
  }
  
  if (typeof apiMapsVersion != "undefined") {
    apiMapsVersion = $("#apiMapsVersion").val();
  }
  
  if (isDesktopEddy) {
    $(function(){
      const $col = $('.colum_move');
      const $container = $('.param_move');
      const $footer = $('#bottom-box');

      if (!$col.length || !$container.length) return;
      
      if ($container.css('position') === 'static') $container.css('position', 'relative');
      
      const recalcPositions = () => {
        const colHeight = $col.outerHeight();
        const containerHeight = $container.outerHeight();
        
        if (containerHeight < colHeight) {
          $container.css('min-height', colHeight + 'px');
        }

        return {
          containerTop: $container.offset().top,
          containerBottom: $container.offset().top + $container.outerHeight(),
          containerWidth: $container.outerWidth(),
          containerLeft: $container.offset().left,
          colHeight: $col.outerHeight(),
          colWidth: $col.outerWidth(),
          colBottom: $col.offset().top + $col.outerHeight(),
          footerTop: $footer.offset().top
        };
      };
      
      let pos = recalcPositions();
      
      const update = () => {
        pos = recalcPositions();
        const scrollTop = $(window).scrollTop();

        if (pos.containerBottom - pos.containerTop < pos.colHeight) {
          $col.css({ position: '', top: '', left: '', width: '' }).removeClass('at-bottom');
          return;
        }

        let maxTop = pos.containerBottom - pos.colHeight;
        maxTop = maxTop < pos.containerTop ? pos.containerTop : maxTop;
        
        const fixedLeft = pos.containerLeft + pos.containerWidth - pos.colWidth - 10;
        
        if (scrollTop >= pos.containerTop && scrollTop <= maxTop) {
          $col.css({
            position: 'fixed',
            top: '0px',
            left: fixedLeft + 'px',
            width: pos.colWidth + 'px'
          }).removeClass('at-bottom');
        } else if (scrollTop > maxTop && pos.colBottom < pos.footerTop) {
          const absoluteTop = maxTop - pos.containerTop;
          $col.css({
            position: 'absolute',
            top: absoluteTop + 'px',
            left: (pos.containerWidth - pos.colWidth - 10) + 'px',
            width: pos.colWidth + 'px'
          }).addClass('at-bottom');
        } else {
          $col.css({ position: '', top: '', left: '', width: '' }).removeClass('at-bottom');
        }
      };
      
      $(window).on('scroll resize load', () => {
        if (event.type === 'resize') {
          setTimeout(() => { update(); }, 50);
        } else {
          update();
        }
      });
      
      update();
    });
  }
});

function setAddress(){
  const placeId = $('#addressPlaceId').val();
  const number = $('#addressNumber').val();
  if (placeId && number) {
    Cookies.set('addressED', {placeId, number});
  }
}

function checkRedirectCombo(){
  const combo = $('#comboRedirect').val();
  if (combo) {
    window.location.href = `/combo/${combo}`;
  }
}

function renderServiceHoursToday(){
  serviceHours = $('#serviceHours').val();
  if (serviceHours) {
    serviceHours = JSON.parse(serviceHours);
  }

  serviceHoursToday = $('#serviceHoursToday').val();
  if (serviceHoursToday.length > 0) {
    htmlServiceHoursToday = `<span>${serviceHoursToday}</span><br>`;
  }

  if (serviceHours) {
    htmlServiceHoursToday += `<span class="linkModalServiceHours">Confira os horários de atendimento</span>`;
  } else {
    let descriptionOld = $('#serviceHoursOld').val();
    htmlServiceHoursToday = `<span>${descriptionOld}</span>`;
  }

  $('#hrrios').html(htmlServiceHoursToday);
  $('.avisohorarioatendimento').html(htmlServiceHoursToday);
  $('.info_meupedido.horario').html(htmlServiceHoursToday);
  if (serviceHoursToday.length > 0) {
    $('#info_horarioatend span').html(htmlServiceHoursToday);
  } else {
    $('#info_horarioatend').html(htmlServiceHoursToday);
  }
}

function openModalServiceHours(){
  if (!serviceHours) {
    Swal({
      type: 'info',
      title: 'Horário de Atendimento',
      html: 'Entre em contato com o estabelecimento para mais informações.'
    });
    return;
  }

  const daysOfWeek = {
    0: 'Domingo',
    1: 'Segunda-feira',
    2: 'Terça-feira',
    3: 'Quarta-feira',
    4: 'Quinta-feira',
    5: 'Sexta-feira',
    6: 'Sábado'
  }

  let html = '';

  const keysDaysOfWeek = Object.keys(daysOfWeek);
  for (let i = 0; i < keysDaysOfWeek.length; i++) {  
    const serviceDay = serviceHours[i];
    let hours = "";
    let closed = false;

    if (serviceDay) {
      for (let x = 0; x < serviceDay.length; x++) {
        hours += `${serviceDay[x][0]} às ${serviceDay[x][1]}`;
        if (x < serviceDay.length - 1) {
          hours += '<br>'
        }
      }
    } else {
      hours = "Fechado";
      closed = true;
    }
    let div = `<div class='mdl-list__item divModalServiceHour' ${closed ? "style='color: red;'" : ""}>
        <span><b>${daysOfWeek[i]}</b></span>
        <span>${hours}</span></div>`;

    html += div;
  }

  Swal({
    type: 'info',
    title: 'Horários de Atendimento',
    html: html
  });
}

function showNotification(){
  if(comunicado){
    var id_comunicado = comunicado.ID;

    // Verificar se já exibiu esse comunicado
    if(Cookies.get('show_comunicado_'+cod_filial+'_'+id_comunicado) == undefined){
      const titulo = comunicado.TITULO;
      const msg = comunicado.MSG;
      
      const dataSwal = {
        title: titulo,
        html: msg,
        confirmButtonText: comunicado["TEXTO_BOTAO"].length > 0 ? comunicado["TEXTO_BOTAO"] : "OK",
        allowOutsideClick: false,
        allowEscapeKey: false,
        customClass: 'sweet-notification-app',
        showCloseButton: true,
        allowOutsideClick: true,
        onClose: function(){
          Cookies.set('show_comunicado_'+cod_filial+'_'+id_comunicado, "sim", { expires: 1 });
          aplicaCupomUrl();
        },
        onOpen: () => {
          const image = document.querySelector('.swal2-image');
          if (image) {
            image.addEventListener('click', () => swal.clickConfirm());
          }
        }
      }
    
      if (comunicado["FOTO_ID"]) {
        const imagePath = `banners/${comunicado["FOTO_ID"]}/${comunicado["FOTO_NOME"]}`;
        dataSwal["imageUrl"] = urlsfiles.imagens + imagePath;
      }
    
      if (comunicado["ICONE"]) dataSwal["type"] = comunicado["ICONE"];
    
      Swal(dataSwal).then((value) => {
        if (value?.value) {
          if (comunicado["URL_DESTINO"]) window.location.href = comunicado["URL_DESTINO"];
        }
      });
      return;
    }
  }
  aplicaCupomUrl();
}

function showNotificationPauseDeliveryOnline(){
  if (!pauseDeliveryOnline["status"]) return;

  const pathname = window.location.pathname;

  const singleViewPages = [
    "/cardapio/",
    "/"
  ]

  const isSingleView = singleViewPages.find( p => p == pathname);

  if (isMobile && isSingleView) {
    const getCookie = Cookies.get("notification-pause-delivery-ed");
    if (getCookie && getCookie.includes(`|${pathname}|`)) {
      return;
    }
  }

  const start = new Date(pauseDeliveryOnline["date"]);
  const end = new Date(start.getTime() + pauseDeliveryOnline["time"] * 60 * 1000);

  const timeToOpenInMs = (end.getTime() - new Date().getTime());
  let timeToOpenInMinutes = Math.round(timeToOpenInMs / 1000 / 60);
  if (timeToOpenInMinutes == -1) timeToOpenInMinutes = 1;
  const elementTimeToOpen = timeToOpenInMinutes > 1 ? `${timeToOpenInMinutes} minutos` : `${timeToOpenInMinutes} minuto`;

  const notification = new ToastNotification("notification-pause-delivery", "info", "Já voltamos!", `Estamos fazendo uma pausa rápida.<br>Em <span id='time-to-open-pause-delivery'>${elementTimeToOpen}</span>, voltaremos a aceitar pedidos!`, false, false);

  if (isDesktopEddy) {
    $(notification.getRender()).insertAfter("#pedido-dir");
    $(".avisoatendimentofora").hide();
  } else {
    if (pathname.includes("meu-pedido")) {
      $(notification.getRender()).insertAfter("#total-finaliza-ped");
    } else {
      if (isSingleView) {
        const cookieTimeExpire = new Date(new Date().getTime() + timeToOpenInMs + 3000);
        const callBackClose = () => {
          let cookieBody = `|${pathname}|`;
          const getCookie = Cookies.get("notification-pause-delivery-ed");
          if (getCookie) {
            cookieBody += getCookie;
          }

          Cookies.set("notification-pause-delivery-ed", cookieBody, { expires: cookieTimeExpire })
        }

        notification.showClose = true;
        notification.callBackClose = callBackClose;
        $("#notificationDeliveryClosed").html(notification.getRender())
      }
    }
  }

  let timeToNextMinuteTimeEnd = timeToOpenInMs % 60000;

  setTimeout(() => {
    intervalNotificationPauseDeliveryOnline = setInterval(() => {
      updateTimeNotifications("time-to-open-pause-delivery", end);
    }, 60000);

    updateTimeNotifications("time-to-open-pause-delivery", end);
  }, timeToNextMinuteTimeEnd)

  setTimeout(() => {
    if (intervalNotificationPauseDeliveryOnline) clearInterval(intervalNotificationPauseDeliveryOnline);
    $("#notification-pause-delivery").remove();
  }, timeToOpenInMs);
}

function updateTimeNotifications(elementId, end) {
  const timeInMs = (end.getTime() - new Date().getTime());
  let timeInMinutes = Math.round(timeInMs / 1000 / 60);
  if (timeInMinutes == -1) timeInMinutes = 1;
  
  const elementTimeToOpen = timeInMinutes > 1 ? `${timeInMinutes} minutos` : `${timeInMinutes} minuto`;

  $(`#${elementId}`).html(elementTimeToOpen);
}

function showNotificationAroundClosingTime(){
  if (pauseDeliveryOnline["status"]) return;

  const pathname = window.location.pathname;

  const singleViewPages = [
    "/cardapio/",
    "/"
  ]

  const isSingleView = singleViewPages.find( p => p == pathname);

  if (isMobile && isSingleView) {
    const getCookie = Cookies.get("notification-around-closing-time-ed");
    if (getCookie && getCookie.includes(`|${pathname}|`)) {
      return;
    }
  }

  const timeToCloseInMs = getTimeToCloseInMs();
  if (!timeToCloseInMs || timeToCloseInMs > 900000) { //15 minutos
    return;
  }

  let timeToCloseInMinutes = Math.round(timeToCloseInMs / 1000 / 60);
  if (timeToCloseInMinutes == -1) timeToCloseInMinutes = 1;

  const elementTimeToClosing = timeToCloseInMinutes > 1 ? `${timeToCloseInMinutes} minutos` : `${timeToCloseInMinutes} minuto`;
  const notification = new ToastNotification("notification-around-closing-time", "info", "Ainda dá tempo!", `O nosso atendimento termina em <span id='around-closing-time'>${elementTimeToClosing}</span>. Faça já seu pedido!`, false, false);

  if (isDesktopEddy) {
    $(notification.getRender()).insertAfter("#pedido-dir");
  } else {
    
    if (pathname.includes("meu-pedido")) {
      $(notification.getRender()).insertAfter("#total-finaliza-ped");
    } else {
      if (isSingleView) {
        const cookieTimeExpire = new Date(new Date().getTime() + timeToCloseInMs + 3000);
        const callBackClose = () => {
          let cookieBody = `|${pathname}|`;
          const getCookie = Cookies.get("notification-around-closing-time-ed");
          if (getCookie) {
            cookieBody += getCookie;
          }

          Cookies.set("notification-around-closing-time-ed", cookieBody, { expires: cookieTimeExpire })
        }

        notification.showClose = true;
        notification.callBackClose = callBackClose;
        $("#notificationAroundClosingTime").html(notification.getRender())
      }
    }
  }

  let timeToNextMinuteTimeClose = timeToCloseInMs % 60000;
  const end = new Date(new Date().getTime() + timeToCloseInMs);

  setTimeout(() => {
    intervalNotificationPauseDeliveryOnline = setInterval(() => {
      updateTimeNotifications("around-closing-time", end);
    }, 60000);

    updateTimeNotifications("around-closing-time", end);
  }, timeToNextMinuteTimeClose)

  setTimeout(() => {
    if (intervalNotificationPauseDeliveryOnline) clearInterval(intervalNotificationPauseDeliveryOnline);
    $("#notification-around-closing-time").remove();
  }, timeToCloseInMs);
}

function getTimeToCloseInMs(){
  const now = new Date();
  const nowDate = new Date();
  const dayOfWeek = now.getDay();
  let time = null;

  if (serviceHours.hasOwnProperty(dayOfWeek)) {
    for (let i = 0; i < serviceHours[dayOfWeek].length; i++) {
      let serviceHour = serviceHours[dayOfWeek][i];
      let hourOpen = parseInt(serviceHour[0].split(':')[0]);
      let minutesOpen = parseInt(serviceHour[0].split(':')[1]);
      let hourClose = parseInt(serviceHour[1].split(':')[0]);
      let minutesClose = parseInt(serviceHour[1].split(':')[1]);

      let timeOpen = nowDate.setHours(hourOpen);
      timeOpen = new Date(timeOpen).setMinutes(minutesOpen);
      timeOpen = new Date(timeOpen).setSeconds(0);
      let timeClose = nowDate.setHours(hourClose);
      timeClose = new Date(timeClose).setMinutes(minutesClose);
      timeClose = new Date(timeClose).setSeconds(59);

      if (now >= timeOpen && now < timeClose) {
        time = (new Date(timeClose).getTime() - now.getTime());
        break;
      }
    }
  }

  return time;
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    let r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
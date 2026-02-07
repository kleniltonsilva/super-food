$(document).ready(function(){
  $(".linkbairros").click(function(e){
    showModalBairroAtendidos();
  });

  $(document).on('keyup', '.searchNeighborhood', function (){
    const value = $(this).val();
    
    $(".bairros.showbairro .nomesdosbairros").each(function() {
      let txtelen_x = $(this).text();
      try {
        txtelen_x = txtelen_x.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      } catch (error_ueueb) {}
  
      if (txtelen_x.search(new RegExp(value, "i")) > -1) {
        $(this).removeClass("hideNeighborhood");
      }
      else {
        $(this).addClass("hideNeighborhood");
      }
    }); 
  });
});

function showModalBairroAtendidos(){
  $.pgwModal({
    target: '#modalBairrosAtendidos',
    titleBar: false,
    maxWidth: 740
  });
  $(".pm-content").css("padding","0px");
  $(".pm-body").css("margin-top","30px");

  if (!$(".cidadeatend.cidselecinada").length) {
    $($(".cidadeatend")[0]).click();
  }
  $('.hideNeighborhood').removeClass('hideNeighborhood');
}
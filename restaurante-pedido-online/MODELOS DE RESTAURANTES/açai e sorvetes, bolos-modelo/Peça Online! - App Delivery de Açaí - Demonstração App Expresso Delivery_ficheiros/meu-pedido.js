$(document).ready(function(e){
  $(document).on('click', '.edit_item_kg', function(e){
    const data = {
      name: $(this).data('name'),
      quantitySale: $(this).data('quantitysale'),
      precoitem: parseFloat($(this).data('price')) * 1000,
      quantity: $(this).data('quantity'),
      dataItem: $(this).data('data'),
      description: $(this).data('description'),
      imageURL: $(this).data('imageurl')
    }
    openModalItemKgEdit(data);
  })

  if(isMobile){
    showNotificationPauseDeliveryOnline();
    showNotificationAroundClosingTime();
  }

  $(document).on('click', '.progress-card', function(e){
    const title = $(this).data('title');
    const description = $(this).data('description');

    Swal({
      title: title,
      html: description,
      type: "info",
    }); 
  })
});

function renderPercentageToPromotionDeliveryFee(data){
  if (!data.amount) {
    $("#promotionDeliveryFee").hide();
    return;
  }

  const typeDescription = data.type == "gratis" ? "Frete Grátis" : "Desconto no Frete";

  $("#promotionDeliveryFee").show();
  $("#promotionDeliveryFee .progress-bar").css("width", `${data.percentage}%`)
  $("#promotionDeliveryFee .promotion-amount").html(`R$ ${parseReal(data.amount)}`)
  $("#promotionDeliveryFee .promotion-type").html(typeDescription);
  $("#promotionDeliveryFee").data('title', data.title);
  $("#promotionDeliveryFee").data('description', data.description);
}

function renderPercentageToPromotionBuyAndGet(data){
  if (!data.amount) {
    $("#promotionBuyAndGet").hide();
    return;
  }

  $("#promotionBuyAndGet").show();
  $("#promotionBuyAndGet .progress-bar").css("width", `${data.percentage}%`)
  $("#promotionBuyAndGet .promotion-amount").html(`R$ ${parseReal(data.amount)}`)
  $("#promotionBuyAndGet").data('title', data.title);
  $("#promotionBuyAndGet").data('description', data.description);
}
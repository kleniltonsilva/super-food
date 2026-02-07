let quantityIncrementCurrent = 1;
let itemPriceCurrent = 0;
let itemQuantityCurrent = 1;
let dataItemCurrent = null;
let requestAddItemInProgress = false;

$(document).ready(function(e){
  $(document).on("click", ".clk_botao_itemsimples", function(e){
    const data = $(this).data("dadositem");
    const typeUnit = data['typeUnit'] ?? 'UN';

    if (typeUnit == 'KG') {
      openModalItemKg(data);
      return;
    }

    addItem(data);    
  });

  $(document).on("click", ".clk_botao_itempersonal", function(e){
    if (isDesktopEddy) return;

    const data = $(this).data("dadositem");
    addItem(data);
  });

  $(document).on("click", ".modalAddItem_quantity_increase", function(e) {
    const currentValue = parseInt($('.modalAddItem_quantity_value').val());
    let newQuantity = currentValue + quantityIncrementCurrent;

    if (newQuantity >= 9999) {
      newQuantity = 9999;
    } 

    itemQuantityCurrent = newQuantity

    $('.modalAddItem_quantity_value').val(itemQuantityCurrent).change();
  });

  $(document).on("click", ".modalAddItem_quantity_decrease", function(e) {
    const currentValue = parseInt($('.modalAddItem_quantity_value').val());
    let newQuantity = currentValue - quantityIncrementCurrent;
    if (newQuantity <= quantityIncrementCurrent) {
      newQuantity = quantityIncrementCurrent;
    }

    itemQuantityCurrent = newQuantity

    $('.modalAddItem_quantity_value').val(itemQuantityCurrent).change();
  });

  $(document).on("change", ".modalAddItem_quantity_value", function (e) {
    let quantity = parseInt($(this).val());
    if (quantity > 9999) quantity = 9999;
    if (quantity < 1) quantity = 1;

    $(this).val(quantity);

    itemQuantityCurrent = quantity

    $('#modalAddItem_price').html(`R$ ${parseReal((itemPriceCurrent * itemQuantityCurrent) / divisorCurrent)}`);
  });

  $(document).on("click", ".modalAddItem_btnAddModalItem", function (e){
    if ($(this).parent().parent().hasClass('modalAddItemSlider')) return;
    
    const quantity = $(".modalAddItem_quantity_value").val();

    if ($(this).data('upsellorder')) {
      const itemId = $(this).data('itemid');
      addItemsUpsellOrder([{
        itemId: itemId,
        amount: quantity
      }], 0);
      closeModalEddy();
      return;
    }

    if ($(this).data('upsell')) {
      const itemId = $(this).data('itemid');
      $(`.inputUpsell.produto[data-upsell-itemid="${itemId}"]`).html(quantity);
      $(`.inputUpsell.upsell_additemcart[data-upsell-itemid="${itemId}"]`).html(0);
      closeModalEddy();
      return;
    }

    if ($(this).data('editing')) {
      dataItemCurrent['dataItem']['quantity'] = quantity;
      actionItemOrder(dataItemCurrent['dataItem'], "editQuantity");
      closeModalEddy();
      return;
    }

    dataItemCurrent['quantity'] = quantity;
    addItem(dataItemCurrent);
    closeModalEddy();
  });

  $(document).on("change", ".inputQuantityProduct", function (e){
    const quantity = $(this).val();
    const quantityCurrent = $(this).data('quantity-current');
    const itemData = $(this).parent().data('dadositem');
    const itemOrderId = $(this).parent().data("coditemped");

    if (requestAddItemInProgress) {
      $(this).val(quantityCurrent);
      console.warn("Já existe uma requisição para adicionar item no pedido em andamento.");
      return;
    }

    if (quantity > 999) {
      $(this).val(999).change();
      return;
    }

    if (quantity == 0 && quantityCurrent == 0) return;
    if (quantity == quantityCurrent) return;

    if (quantity == 0 && quantityCurrent > 0) {
      actionItemOrder(null, "deletar", {skeyitem: itemOrderId, origem: "qtd", skeycod: itemData["coditem"], hash: itemData["hashitem"], quantity: 0});
      return;
    }

    itemData["quantity"] = quantity;

    if (quantityCurrent == 0) {
      itemData["origem"] = "qtd";
      addItem(itemData);
      return;
    }

    actionItemOrder(null, "editQuantity", {skeyitem: itemOrderId, origem: "qtd", skeycod: itemData["coditem"], hash: itemData["hashitem"], quantity});
  });

  $(document).on("click", ".decreaseQuantityProduct.qtd_menos", function(e){
    if ($(e.target)[0].className.indexOf("upsell") > -1) return;

    const quantityCurrent = parseInt($(this).next().val());
    if (quantityCurrent > 0) $(this).next().val(quantityCurrent - 1).change();
  });

  $(document).on("click", ".incrementQuantityProduct.qtd_mais", function(e){
    if ($(e.target)[0].className.indexOf("upsell") > -1) return;

    const quantityCurrent = parseInt($(this).prev().val());
    $(this).prev().val(quantityCurrent + 1).change();
  });

  $(document).on("focus", ".inputQuantityProductSummary", function (e){
    $(this).select();
  });

  $(document).on("focus", ".inputQuantityProduct", function (e){
    $(this).select();
  });

  $(document).on("change", ".inputQuantityProductSummary", function (e){
    const quantity = $(this).val();
    const quantityCurrent = $(this).data('quantity-current');
    const itemData = $(this).parent().data('dadosalteracao');
    const itemId = itemData["skeyitem"];

    if (quantity > 999) {
      $(this).val(999).change();
      return;
    }

    if (quantity == quantityCurrent) return;

    itemData["quantity"] = quantity;
    itemData["origem"] = "qtd";

    if (quantity == 0 && quantityCurrent > 0) {
      Swal({
        title: 'Remover Item do Pedido?',
        text: 'Deseja remover esse item do seu pedido?',
        type: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3e9a00',
        cancelButtonColor: '#3085d6',
        cancelButtonText: 'Não',
        confirmButtonText: 'Sim, Remover Item!',
        allowOutsideClick: false,
        allowEscapeKey: false
      }).then(function(result) {
        if (result.value) {
          actionItemOrder(null, "deletar", itemData);
          return;
        }
      
        $(`.inputQuantityProductSummary[data-id="${itemId}"]`).val(quantityCurrent);
      });
      return;
    }

    actionItemOrder(null, "editQuantity", itemData);
  });

  $(document).on("click", ".decreaseQuantityProductSummary.qtd_menos_pedido", function(e){
    const quantityCurrent = parseInt($(this).next().val());
    if (quantityCurrent > 0) $(this).next().val(quantityCurrent - 1).change();
  });

  $(document).on("click", ".incrementQuantityProductSummary.qtd_mais_pedido", function(e){
    const quantityCurrent = parseInt($(this).prev().val());
    $(this).prev().val(quantityCurrent + 1).change();
  });

  $(document).on("change", ".inputQuantityComboSummary", function (e){
    const quantity = $(this).val();
    const quantityCurrent = $(this).data('quantity-current');
    const comboData = $(this).parent().data('dadosalteracao');
    const comboId = $(this).data('id');

    if (quantity > 999) {
      $(this).val(999).change();
      return;
    }

    if (quantity == quantityCurrent) return;

    comboData["quantity"] = quantity;

    if (quantity == 0 && quantityCurrent > 0) {
      Swal({
        title: 'Remover Item do Pedido?',
        text: 'Deseja remover esse item do seu pedido?',
        type: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3e9a00',
        cancelButtonColor: '#3085d6',
        cancelButtonText: 'Não',
        confirmButtonText: 'Sim, Remover Item!',
        allowOutsideClick: false,
        allowEscapeKey: false
      }).then(function(result) {
        if (result.value) {
          actionsCombo(comboData, 'deletar');
          return;
        }

        $(`.inputQuantityComboSummary[data-id="${comboId}"]`).val(quantityCurrent);
      });
      return;
    }

    actionsCombo(comboData, 'editQuantity');
  });

  $(document).on("click", ".decreaseQuantityComboSummary.qtd_menos_pedido", function(e){
    const quantityCurrent = parseInt($(this).next().val());
    if (quantityCurrent > 0) $(this).next().val(quantityCurrent - 1).change();
  });

  $(document).on("click", ".incrementQuantityComboSummary.qtd_mais_pedido", function(e){
    const quantityCurrent = parseInt($(this).prev().val());
    $(this).prev().val(quantityCurrent + 1).change();
  });
});

function addItem(dados){
  if (requestAddItemInProgress) {
    console.warn("Já existe uma requisição para adicionar item no pedido em andamento.");
    return;
  }

  requestAddItemInProgress = true;

  const cookieUpsell = Cookies.get('openUpsellED');
  if (cookieUpsell && cookieUpsell != dados.codtipo) {
    Cookies.remove('openUpsellED');
  }
  $.ajax({
    method: "POST",
    url: "/exec/pedido/adicionaritem",
    data: dados,
    dataType : "json"
  }).done(function( msg ) {
    sessionStorage.removeItem('itemEditingED');
    if(msg.res === true){
      divisorCurrent = 1;

      if(msg.dados !== false){
        if(msg.dados.redirect !== false){
          document.location.href = msg.dados.redirect;
        }
      }else{
        if(msg.iditem != undefined){
          $(`#qtd_${dados["coditem"]}`).parent().data('coditemped', msg.iditem); 
          $(`#qtd_${dados["coditem"]}`).data('quantity-current', dados["quantity"]);
        }

        requestAddItemInProgress = false;
        get_resumoPedido();
        if (typeof showMensagem_baixo == 'function') showMensagem_baixo("✅ Item adicionado com sucesso");

        if(fbp_configurado == true && dados != undefined && dados != null){
          fbq('track', 'AddToCart', {
              content_name: dados.nomeitem, 
              content_category: dados.tiponome,
              content_ids: [dados.coditem],
              content_type: 'product',
              value: dados.precoitem,
              currency: 'BRL'
            },
            {
              eventID: facebookEventID
            }
          );
        }

        if(tiktokpixel_configurado == true && dados != undefined && dados != null){
          ttq.track('AddToCart', {
            content_name: dados.nomeitem, 
            value: dados.precoitem,
            content_category: dados.tiponome,
            content_id: [dados.coditem],
            content_type: 'product',
            currency: 'BRL'
          });
        }

        if (GA4_configurado && dados != undefined && dados != null) {
          gtag("event", "add_to_cart", {
            currency: "BRL",
            value: dados.precoitem,
            items: [
              {
                item_id: dados.coditem,
                item_name: dados.nomeitem,
                item_category: dados.tiponome,
                price: dados.precoitem,
                quantity: 1
              }
            ]
          });
        }

        if(msg.htmlItemsUpsell) {
          if (isDesktopEddy) {
            getModalUpsell(msg.htmlItemsUpsell, dados.codtipo, false, true)
            return;
          }
          getModalUpsell(msg.htmlItemsUpsell, dados.codtipo, dados.codtipo)
        }
      }
      return;
    }   
         
    requestAddItemInProgress = false;
    
    if(msg.indisponibilidade_turno && msg.indisponibilidade_turno == true && msg.turnos_sessao && msg.turnos_sessao.length > 0) {
      Swal({
        title: "Produto Indisponível",
        html: geraMensagemDisponibilidadePorTurno(msg.turnos_sessao),
        type: "warning"                  
      }); 
      return;
    }
    if (msg.delivery_fechado != undefined) {
      Swal({
        title: 'Delivery Online - FECHADO',
        html: htmlServiceHoursToday,
        type: 'info',
      });
    }else{
      Swal({
        type: 'warning',
        title: 'Oops..',
        html: 'Erro ao adicionar item no pedido. Tente novamente mais tarde',
        onClose: () => {
          document.location.reload();
        }
      });   
    }
  });
}

function actionItemOrder(dataItem, action, dataByQuantity = {}){
  if (requestAddItemInProgress) {
    console.warn("Já existe uma requisição para adicionar item no pedido em andamento.");
    return;
  }

  requestAddItemInProgress = true;
  
  const data = {
    dados : dataItem,
    acao : action,
    ...dataByQuantity
  };
  showLoading();

  $.ajax({
    method: "POST",
    url: "/exec/pedido/itempedido",
    data: data,
    dataType : "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){ 
      if(msg.dados != undefined){
        if(msg.dados.acao === "editar"){
          document.location.href = msg.dados.redirect;
        }
      }
      
      if(action === "deletar" && isMobile){
        showMensagem_baixo("Item removido com sucesso.");
      }

      if (action == 'diminuir' || action === 'deletar') {
        let elementsUpsell = $('.inputUpsell.upsell_additemcart');
        for (let i = 0; i < elementsUpsell.length; i++) {
          const element = $(elementsUpsell[i]);
          if (element.data('upsell-itemid') == (dataItem?.skeycod || dataByQuantity?.skeycod)) {
            let currentValue = parseInt(element.html());
            if (currentValue < 1) {
              get_resumoPedido();            
              break;
            }
            element.html(currentValue -1)
            break;
          }
        }
      }

      if (dataByQuantity.hasOwnProperty("skeycod")) {
        $(`#qtd_${dataByQuantity["skeycod"]}`).data('quantity-current', dataByQuantity["quantity"]);
      }

      requestAddItemInProgress = false;
      get_resumoPedido();  
      return;          
    }

    requestAddItemInProgress = false;

    Swal({
      type: 'warning',
      title: 'Oops..',
      html: msg.msg
    });   
  });
}

function openModalItemKg(data, title = null){
  return new Promise((resolve, reject) => {
    itemPriceCurrent = 0;
    divisorCurrent = 1000;
    title = title ? title : "Adicionar Item";
    const modal = new ModalItem("modalAddItem", title, data['name'], "<div class='info-alert'>ℹ️ Produtos por kg podem variar na pesagem. Faremos o possível para chegar o mais próximo do seu pedido.</div>Selecione a quantidade desejada <strong>em gramas</strong>:", data['imageURL'], data['description'], '#modalEddy');
    modal.build();
  
    quantityIncrementCurrent = parseInt(data["quantitySale"]);
    itemPriceCurrent = data["precoitem"];
    dataItemCurrent = data;
    $('.modalAddItem_quantity_value').attr('disabled', 'disabled');
    $('.modalAddItem_quantity_value').val(quantityIncrementCurrent).change();
    openModalEddy();
    resolve(true);
  })
}

async function openModalItemKgEdit(data) {
  await openModalItemKg(data, "Editar Item");
  divisorCurrent = 1000;
  const quantity = parseInt(data['quantity']);
  $('.modalAddItem_quantity_value').val(quantity).change();
  $('.btnAddModalItem').data('editing', true);
}

async function openModalItemKgUpsell(data){
  await openModalItemKg(data);
  divisorCurrent = 1000;
  const quantity = parseInt(data['quantity']);
  $('.modalAddItem_quantity_value').val(quantity).change();
  $('.btnAddModalItem').data('upsell', true);
  $('.btnAddModalItem').data('itemid', data['itemId']);

  if (data.upsellOrder) {
    $('.btnAddModalItem').data('upsellorder', true);
  }
}
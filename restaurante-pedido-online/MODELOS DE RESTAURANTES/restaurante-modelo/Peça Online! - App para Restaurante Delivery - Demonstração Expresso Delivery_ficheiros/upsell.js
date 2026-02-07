$(document).ready(function(e){
  $(document).on('click', '.qtd_menos_upsell.upsell_montador', async function(e){
    let itemId = $(this).data('upsell-itemid');
    let input = $(`.inputUpsell.upsell_montador[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    if (currentValue < 1) return;
    input.html(currentValue -1);
    let upsellItems = await getUpsellItemsProduct();
    if (upsellItems) {
      Cookies.set('upsellItemsMontadorED', JSON.stringify(upsellItems));
    } else {
      Cookies.remove('upsellItemsMontadorED');
    }
  });

  $(document).on('click', '.qtd_mais_upsell.upsell_montador', async function(e){
    let itemId = $(this).data('upsell-itemid');
    let input = $(`.inputUpsell.upsell_montador[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    input.html(currentValue + 1);
    let upsellItems = await getUpsellItemsProduct();
    if (upsellItems) {
      Cookies.set('upsellItemsMontadorED', JSON.stringify(upsellItems));
    }
  });

  $(document).on('click', '.qtd_menos_upsell.upsell_montador_padrao_desktop', async function(e){
    let itemId = $(this).data('upsell-itemid');
    let input = $(`.inputUpsell.upsell_montador_padrao_desktop[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    if (currentValue < 1) return;
    input.html(currentValue -1);
  });

  $(document).on('click', '.qtd_mais_upsell.upsell_montador_padrao_desktop', async function(e){
    let itemId = $(this).data('upsell-itemid');
    let input = $(`.inputUpsell.upsell_montador_padrao_desktop[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    input.html(currentValue + 1);
  });

  $(document).on('click', '.qtd_menos_upsell.upsell_additemcart', async function(e){
    const originInputId = $(this).parent().parent().parent().parent().parent().parent().attr('id');
    let itemId = $(this).data('upsell-itemid');
    let input = $(`#${originInputId} .inputUpsell.upsell_additemcart[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    if (currentValue < 1) return;

    let itemsCart = $('.qtd_item');
    if (itemsCart.length < 1) return;
    for (let i = 0; i < itemsCart.length; i++) {
      const elementItem = $(itemsCart[i]);
      const dadosalteracao = elementItem.data('dadosalteracao');
      if (dadosalteracao['skeycod'] == itemId) {
        const elementsQtd = elementItem.children();
        for (let x = 0; x < elementsQtd.length; x++) {
            let element = $(elementsQtd[x]);
            if (element.hasClass('addmenos_item')) {
                element.click();
                break;
            }
        }
      }
    }
  });

  $(document).on('click', '.qtd_mais_upsell.upsell_additemcart', async function(e){
    if ($(this).hasClass('addItemKgUpsell')) return;

    const originInputId = $(this).parent().parent().parent().parent().parent().parent().attr('id');
    let itemId = $(this).data('upsell-itemid');
    let input = $(`#${originInputId} .inputUpsell.upsell_additemcart[data-upsell-itemid="${itemId}"]`);
    let currentValue = parseInt(input.html());
    input.html(currentValue + 1);
    const items = [{
        itemId: itemId,
        amount: 1
    }];

    if ($(this).hasClass('produto')) {
      addItemsUpsellOrder(items, $(this).data('upsell-sessionid'), input);
      return;
    }
    addItemsUpsellOrder(items, 0, input);
  });
  
  setTimeout(function(){
    let owlitensUpsell = $('#slide-upsell');
    if (owlitensUpsell.length > 0) {
      owlitensUpsell.owlCarousel({
          itemsCustom : [
              [0, 2],
              [960, 4]
          ],
          navigation : false,
          pagination : false,
          autoPlay: 4000,
          stopOnHover : true
      });
      $('.next-upsell').click(function() {
        owlitensUpsell.trigger('owl.next');
      });
      $('.prev-upsell').click(function() {
        owlitensUpsell.trigger('owl.prev');
      });
    }

    let owlitensUpsellPedido = $('#slide-upsellpedido');
    if (owlitensUpsellPedido.length > 0) {
      owlitensUpsellPedido.owlCarousel({
          itemsCustom : [
              [0, 2],
              [960, 2]
          ],
          navigation : false,
          pagination : false,
          autoPlay: 4000,
          stopOnHover : true
      });
      $('.next-upsell').click(function() {
        owlitensUpsellPedido.trigger('owl.next');
      });
      $('.prev-upsell').click(function() {
        owlitensUpsellPedido.trigger('owl.prev');
      });
    }
  }, 800);

  $(document).on("click", ".addItemKgUpsell", function(e){
    const itemId = $(this).data('itemid');
    const upsellOrder = $(this).hasClass('upsell_additemcart');
    let quantity = $(`.inputUpsell[data-upsell-itemid="${itemId}"]`).html();
    quantity = quantity > 0 ? quantity : $(this).data('quantitysale');
    

    const data = {
      itemId: itemId,
      name: $(this).data('name'),
      quantitySale: $(this).data('quantitysale'),
      precoitem: parseFloat($(this).data('price')),
      quantity: quantity,
      upsellOrder,
      description: $(this).data('description'),
      imageURL: $(this).data('imageurl')
    }

    $('.backdrop').css('z-index', 10000);
    $('.modalEddy').css('z-index', 10001);
    openModalItemKgUpsell(data);
  })
});

function getUpsellItemsProduct(montador = '.upsell_montador'){
  return new Promise((resolve, reject) => {
    let itemsUpsell = [];
    let inputUpsell = Array.from($(`.inputUpsell${montador}`));
    if (inputUpsell.length < 1) {
      resolve(false);
      return;
    }

    for (let i = 0; i < inputUpsell.length; i++) {
      const element = inputUpsell[i];
      const amount = $(element).html();
      if (parseInt(amount) < 1) continue;

      itemsUpsell.push({
        itemId: $(element).data('upsell-itemid'),
        amount,
        price: $(element).data('upsell-price'),
        sessionName: $(element).data('upsell-sessionname'),
        itemName: $(element).data('upsell-itemname')
      });
    }

    if (itemsUpsell.length < 1) {
      resolve(false);
      return;
    }
    resolve(itemsUpsell);
  });
}

function getModalUpsell(htmlItems, sessionOrigin, sessionId = false, desktop = false){
  $('#upsell_montador_padrao_desktop').html('');
  let htmlModalUpsell = "<div class='content_mdl-modal'>";
  htmlModalUpsell += htmlItems;
  htmlModalUpsell += "<div class='clear'></div></div>";

  sessionId = sessionId || true;

  Cookies.set('openUpsellED', sessionId, { expires: 0.5 }); //12h
  const cssDesktop = desktop ? {'max-width': '350px', 'height': '90vh'} : null;
  const classDesktop = desktop ? 'desktop' : null;
  showDialog({
      text: htmlModalUpsell,
      contentStyle: cssDesktop,
      addClass: classDesktop,
      contentStyleButtons: 'display:flex;justify-content:space-between;',
      cancelable: false,
      negative: {
          title: 'Fechar'
      },
      positive: {
        title: '<div class="btn_add_upsell" style="background: #009a00;color: #fff;padding: 0 12px;border-radius: 5px;">Adicionar ao pedido</div>',
        onClick: async () => {
          let isDesktopEddy = classDesktop == 'desktop' ? '.upsell_montador_padrao_desktop' : '.upsell_montador';
          const upsellItemsAdd = await getUpsellItemsProduct(isDesktopEddy);
          if (!upsellItemsAdd) {
            $('#negative').click();
            return;
          }
          addItemsUpsellOrder(upsellItemsAdd, sessionOrigin);
        }
    },
  });
}

function addUpsellMontadorPadraoDesktop(html){
  $(`<div id="upsell_montador_padrao_desktop">${html}</div>`).insertBefore('#btncomprar_montmodal');
  let owlitensUpsellDesktop = $('#slide-upsell');
  if (owlitensUpsellDesktop.length > 0) {
    owlitensUpsellDesktop.owlCarousel({
        itemsCustom : [
            [0, 3],
            [960, 4]
        ],
        navigation : false,
        pagination : false,
        autoPlay: 4000,
        stopOnHover : true
    });
    $('.next-upsell').click(function() {
      owlitensUpsellDesktop.trigger('owl.next');
    });
    $('.prev-upsell').click(function() {
      owlitensUpsellDesktop.trigger('owl.prev');
    });
  }
}

function addItemsUpsellOrder(items, sessionOrigin, input = false){
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/pedido/adicionaritemsupsell",
    data: {items, sessionOrigin},
    dataType : "json",
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){              
      get_resumoPedido();

      for (let i = 0; i < items.length; i++) {
        if(fbp_configurado == true){
          fbq('track', 'AddToCart', {
            content_name: items[i].itemName, 
            content_category: items[i].sessionName,
            content_ids: [items[i].itemId],
            content_type: 'product',
            value: items[i].price,
            currency: 'BRL'
          },
          {
            eventID: facebookEventID
          }
          );
        }

        if(tiktokpixel_configurado == true){
          ttq.track('AddToCart', {
            content_name: items[i].itemName, 
            value: items[i].price,
            content_category: items[i].sessionName,
            content_id: [items[i].itemId],
            content_type: 'product',
            currency: 'BRL'
          });
        }

        if (GA4_configurado) {
          gtag("event", "add_to_cart", {
              currency: "BRL",
              value: items[i].price,
              items: [
                {
                  item_id: items[i].itemId,
                  item_name: items[i].itemName,
                  item_category: items[i].sessionName,
                  price: items[i].price,
                  quantity: items[i].amount
                }
              ]
          });
        }
      }
      $('#negative').click();
      if (typeof showMensagem_baixo == 'function') {
        showMensagem_baixo("✅ Item adicionado com sucesso");
      }
      return;
    }

    if (input) {
      input.html(parseInt(input.html() - 1));
    }

    if(msg.delivery_fechado && msg.delivery_fechado == true){
      Swal({
        type: 'info',
        title: 'Delivery Online - Fechado',
        html: htmlServiceHoursToday
      });
      return;
    }

    Swal({
      type: 'warning',
      title: 'Oops..',
      html: 'Erro ao adicionar item no pedido. Tente novamente mais tarde',
      onClose: () => {
          document.location.reload();
      }
    }); 
  });
}

function resetAmountUpsell(){
  $(`.inputUpsell`).html(0)
}

function additemUpsell(dados){
    dados.origem = 'qtd';

    showLoading();
    $.ajax({
        method: "POST",
        url: "/exec/pedido/adicionaritem",
        data: dados,
        dataType : "json",
        context: this
    }).done(function( msg ) {
        if(msg.res === true){
            if(msg.iditem != undefined){
                $(this).prev().text(msg.qtdatual);
                $(this).parent().data('coditemped', msg.iditem); 
            }
            
            get_resumoPedido();            

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
                    content_id: [dados.coditem],
                    content_type: 'product',
                    content_category: dados.tiponome,
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

            return;
        }

        hideLoading();
        Swal({
            type: 'warning',
            title: 'Oops..',
            html: 'Erro ao adicionar item no pedido. Tente novamente mais tarde',
            onClose: () => {
                document.location.reload();
            }
        });
    });
}
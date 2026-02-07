let comboItems = [];
let comboReadyItems = [];
let currentComboItemQuantity = 0;
let comboDataEditing = {
  editing: {},
  default: {}
};
let comboItemsEditing = {};
let requestNewComboInProgress = false;

$(document).ready(function (e) {
  const orderComboData = $('#orderComboData').val();
  if (orderComboData) {
    comboDataEditing['editing'] = JSON.parse(orderComboData);
  }

  $(document).on("focus", ".comboItemAmount", function (e) {
    let amount = $(this).val();
    currentItemQuantity = amount;
  });

  $(document).on("change", ".comboItemAmount", function (e) {
    let amount = $(this).val();

    if (amount > 1000) {
      $(this).val(1000);
      amount = 1000;
    }

    set_itemSimples($(this).parent().find('.addmaisitem'), "alterar_x", false, $(this));
  });

  $(document).on("focus", ".comboItem_quantity_value", function (e) {
    const itemId = $(this).data('itemid');
    const card = $(`.component_list_items_item[data-comboitem-itemid="${itemId}"]`);
    if (card.hasClass('item_indisponivel')) {
      $(this).blur();
      return;
    }

    let amount = parseInt($(this).val());
    currentItemQuantity = amount;
  }); 

  $(document).on("change", ".comboItem_quantity_value", function (e) {
    let amount = parseInt($(this).val());
    if (isNaN(amount)) amount = 0;
    const itemId = $(this).data('itemid');
    const codConf = $(this).data('combocodconf');
    const allowedQuantity = parseInt($(this).data('comboallowedquantity'));
    const sizeId = $(this).data('sizeid') ?? null;

    const currentQuantity = getQuantityItemCombo(codConf, itemId, sizeId);
    const remainingValue = allowedQuantity - (getTotalQuantityComboByCodConf(codConf) - currentQuantity);
    if (amount > remainingValue) amount = remainingValue;

    if (sizeId) {
      $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"][data-sizeid="${sizeId}"]`).val(amount);
    } else {
      $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"]`).val(amount);
    }

    setQuantityItemCombo(codConf, itemId, amount, sizeId);
  });

  $(document).on("click", ".component_list_items_selector_editor_card_comboItem", async function(e){
    const data  = $(this).data("itemdata");
    const comboStatus = $('#comboStatus').val();
    if (comboStatus == 'new') {
      const comboData = JSON.parse($('#comboData').val());
      const newCombo = await startCombo(comboData);
      setComboItemsEditingStorage();
      data['data_hascombo'] = newCombo['hash'];
      $('#comboStatus').val('editing');
      if (typeof modalComboCurrent != 'undefined' && modalComboCurrent) {
        modalComboCurrent.updateHashDataCombo(newCombo['hash']);
      }
    } else {
      if (!data["data_hascombo"]) {
        data["data_hascombo"] = comboDataEditing['editing']["hash"];
      }
    }
  
    setItemCustomizableCombo(data);
  });

  $(document).on("click", ".component_list_items_selector_editor_card_comboItemReadyCustomizable", async function(e){
    if ($(e.target).html() == "close" || $(e.target).hasClass("component_list_items_remove_item_comboItemReadyCustomizable")) return;
    
    const urlEditor = $(this).data("urleditor");
    if (urlEditor != "edit" && isMobile) {
      window.location.href = urlEditor;
      return;
    }

    const itemData = $(this).data("itemdata");
    const codConf = itemData["data_codconfcombo"];
    const item = comboItems.find(x => x["codConf"] == codConf);

    const itemRender = {
      hasitem: item["itemReady"][0]["itemData"]["item_hash"],
      itemrend: item["itemReady"][0]["itemData"], 
      options: item
    }
    renderEditorItemCombo(itemRender);
  });

  $(document).on('click', '.comboItem_quantity_increase', function(e){
    const codConf = $(this).data('combocodconf');
    const allowedQuantity = $(this).data('comboallowedquantity');
    const itemId = $(this).data('itemid');
    const sizeId = $(this).data('sizeid');

    const card = $(`.component_list_items_item[data-comboitem-itemid="${itemId}"]`);
    if (card.hasClass('item_indisponivel')) return;

    if (getTotalQuantityComboByCodConf(codConf) >= parseInt(allowedQuantity)) return;

    const currentQuantity = getQuantityItemCombo(codConf, itemId, sizeId);

    if (sizeId) {
      $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"][data-sizeid="${sizeId}"]`).val(currentQuantity + 1).change();
      return;
    }
    $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"]`).val(currentQuantity + 1).change();
  });

  $(document).on('click', '.comboItem_quantity_decrease', function(e){
    const codConf = $(this).data('combocodconf');
    const itemId = $(this).data('itemid');
    const sizeId = $(this).data('sizeid');

    const card = $(`.component_list_items_item[data-comboitem-itemid="${itemId}"]`);
    if (card.hasClass('item_indisponivel')) return;

    const currentQuantity = getQuantityItemCombo(codConf, itemId, sizeId);
    if (currentQuantity == 0) return;

    if (sizeId) {
      $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"][data-sizeid="${sizeId}"]`).val(currentQuantity - 1).change();
      return;
    }
    $(`.comboItem_quantity_value[data-combocodconf="${codConf}"][data-itemid="${itemId}"]`).val(currentQuantity - 1).change();
  });

  $(document).on('click', '.comboItem_selector_radio_input', function(e){
    const codConf = $(this).data('combocodconf');
    const itemId = $(this).val();
    const sizeId = $(this).data('sizeid');
    const quantity = $(this).data('quantity') ?? 1;

    const card = $(`.component_list_items_item[data-comboitem-itemid="${itemId}"]`);
    if (card.hasClass('item_indisponivel')) {
      $(this).prop('checked', false);
      $(this).parent().removeClass('is-checked');
      return;
    }

    if (comboItemsEditing[codConf]) delete comboItemsEditing[codConf];

    setQuantityItemCombo(codConf, itemId, quantity, sizeId);
  });

  $(document).on("click", "#btn_finalizar_combo", async function(e){
    if($(this).hasClass("btninativo")){
      Swal({
        type: 'warning',
        title: 'Selecione Todos os Itens',
        text: 'É necessário selecionar todos os produtos do combo para adicioná-lo ao pedido.'
      });  
      return;
    }
    
    const comboData = JSON.parse($('#comboData').val());
    let comboCod = comboData['data_cod'];
    let comboHash = comboData['data_hash'] ?? null;

    const comboStatus = $('#comboStatus').val();
    if (comboStatus == 'new') {
      const newCombo = await startCombo(comboData);
      setComboItemsEditingStorage();
      comboHash = newCombo['hash'];
      $('#comboStatus').val('editing');
      if (typeof modalComboCurrent != 'undefined' && modalComboCurrent) {
        modalComboCurrent.updateHashDataCombo(newCombo['hash']);
      }
    }

    const items = Object.keys(comboItemsEditing).length > 0 ? comboItemsEditing : null;
    if (items) {
      await checkComboComplete(true);
    }

    finishCombo(comboHash, comboCod, items);
  });

  $(document).on("click", ".component_list_items_remove_item_comboItemReadyCustomizable", function(e){
    e.preventDefault();
    const itemHash = $(this).data('itemid');
    const codConf = $(this).data('combocodconf');
    const orderComboId = comboDataEditing['editing']['codigo'];
    removeItemCombo(orderComboId, codConf, itemHash)
  });
});

function renderListItemsCombo() {
  if (typeof comboItems == 'undefined') return;
  
  $('.component_modal_combo_items').html('');
  for (const item of comboItems) {
    const type = item["type"];
    const quantity = item["quantity"];
    const items = type == "comboItemReadyCustomizable" ? item["itemReady"] : item["items"];
    let title = item["items"][0]['sabor_sessaonome'] || item["items"][0]['itemSessionName'];
    let description = quantity > 1 ? `Selecione no total, ${quantity} itens` : "Selecione no total, 1 item";
    let comboData = item["comboData"] ?? false;
    comboData = comboData ? JSON.parse(comboData) : false;
    const info = {
      allowedQuantity: quantity,
      allowsEditing: item["allowsEditing"] ?? false,
      comboData: comboData,
      urlEditor: item['urlEditor'] ?? null,
      sessionName: title
    }

    comboDataEditing['default'][comboData['data_codconfcombo']] = info;

    if (type == 'comboItemReadyCustomizable' || (item['urlEditor'] && item['urlEditor'] == 'new')) {
      title = item["sessionName"];
      description = '';
    }

    description = type == 'comboItem' ? description : '';
    const list = new ListItems(type, title, description, info, items);
    const render = list.getRender();
    $('.component_modal_combo_items').append(render);
    componentHandler.upgradeDom();
  }

  setComboReadyItems();
}

function setItemCustomizableCombo(data){
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/setitemcombo/",
    data: data,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if (msg.res === true) {
      if (isMobile) {
        const comboLink = $('#comboLink').val();
        document.location.href = `/combo/${comboLink}/${comboDataEditing['editing']['codigo']}/item/${data['data_codconfcombo']}/`;
        return;
      }
      
      for (let i = 0; comboItems.length; i++) {
        if (comboItems[i]["codConf"] == data.data_codconfcombo) {
          comboItems[i]["hasitem"] = msg.dados["hasitem"];
          msg.dados.options = comboItems[i];
          msg.dados.options["items"] = comboItems[i]?.flavors ? comboItems[i]?.flavors : comboItems[i]["items"];
          msg.dados.itemrend["hashItemCombo"] = data["data_hashitem"];
          renderEditorItemCombo(msg.dados);
          return;
        }
      }
    }
    
    if(msg.erro_msg != undefined){
      Swal({
        type: "error",
        title: "Oops..",
        html: msg.erro_msg,
        onClose: () => {
          document.location.reload();
        }
      }); 
    } 

    if (msg["type"] && msg["type"] == "item-added") {
      editorGenericCurrent = new EditorGeneric(msg['item'], msg['item']["item_hash"], null, '.component_modal_combo_items', false, "", {codConf: msg.data["codconfitem"]});
      (async () => {
        await setItemReadyComboItems();
        renderListItemsCombo();
        
        setTimeout(function(){
          $(`.comboItemReadyCustomizable_component_list_items_item[data-codconf='${msg.data["codconfitem"]}']`).click();
        }, 500);
      })();

      return;
    }

    Swal({
      type: "error",
      title: "Oops..",
      html: msg.msg,
    }); 
  }).fail(function (jqXHR, textStatus) {
    Swal({
      type: "error",
      title: "Erro ao adicionar item",
      text: "Ocorreu um erro.\n Tente novamente mais tarde.",
    });
  });; 
}

function startCombo(comboData) {
  return new Promise(function(resolve, reject) {
    if (requestNewComboInProgress) {
      reject('requestNewComboInProgress');
      return;
    }

    requestNewComboInProgress = true;
    showLoading();
    $.ajax({
      method: "POST",
      url: "/exec/montadoritem/iniciarcombo/",
      data: comboData,
      dataType : "json"
    }).done(function( msg ) {
      hideLoading();
      requestNewComboInProgress = false;
      if(msg.res === true){
        comboDataEditing['editing'] = msg.dados;
        resolve(msg.dados);
        return;
      }else if(msg.res === false){
        if (msg.dados && msg.dados.disabledItems && Object.keys(msg.dados.disabledItems).length > 0) {
          let categoriesDisabled = msg.dados.disabledItems;
          const factoryMsg = function() {
            let categories = Object.keys(categoriesDisabled).map(e => categoriesDisabled[e]);
            let html = "<div style='text-align: left;padding-left:15px;'>";
            for (let i = 0; i < categories.length; i++) {
              html += `<li><strong>${categories[i]}</strong></li>`;
            }
    
            html += '</div>';
            html = `<span style="text-align: left; display:block;">Os itens das categorias abaixo estão indisponíveis:</span>${html}`
            return html;
          };
  
          Swal({
            type: 'info',
            title: 'Combo Indisponível',
            html: factoryMsg(),
            onClose: () => {
              window.location.href = '/cardapio'
            }
          });
          reject('itens indisponiveis');
          return;
        }
  
        Swal({
          type: 'info',
          title: 'Combo Indisponível',
          text: msg.msg,
          onClose: () => {
            window.location.href = '/cardapio'
          }
        });
        reject(msg.msg);
        return;
      }else{
        Swal({
          type: 'error',
          title: 'Erro ao Acessar Combo.',
          text: 'Atualize a página ou tente novamente mais tarde.'
        });
        reject('Erro ao acessar combo');
        return;
      }
    }).fail(function(esd,sde){
      requestNewComboInProgress = false;
      Swal({
        type: 'error',
        title: 'Erro ao Acessar Combo.',
        text: 'Atualize a página ou tente novamente mais tarde.'
      });
      hideLoading();
      reject('Erro ao acessar combo - Error 5xx');
      return;
    });
  })
}

function finishCombo(hash, cod, items = null){
  const payload = {
    data_hash: hash,
    data_cod: cod
  }

  if (items) payload['items'] = items;

  showLoading();               
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/finalizacombo/",
    data: payload,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){
      if (isMobile) {
        document.location.href = "/meu-pedido/";
      } else {
        get_resumoPedido();    
        closeModalEddy();
      }
      return;
    }

    if (msg.data != undefined && msg.data.codconfitem != undefined && msg.msg != undefined && msg.type != "item") {
      Swal({
        type: "info",
        title: msg.msg,
        text: "Essa opção para o item:"+$("#itemcombo_conf_"+msg.data.codconfitem+" p").text()+", é obrigatória.",
        onClose: () => {
          $("#itemcombo_conf_"+msg.data.codconfitem+".clk_inicombo").trigger("click");
        },
      });
      return;
    }

    if (msg.erro_msg != undefined) {
      Swal({
        type: "error",
        title: "Oops..",
        html: msg.erro_msg,
        onClose: () => {
          document.location.reload();
        }
      }); 
    } 

    if (msg.msgTitle) {
      if (msg["type"] && msg["type"] == "item") {
        editorGenericCurrent = new EditorGeneric(msg['item'], msg['item']["item_hash"], null, '.component_modal_combo_items', false, "", {codConf: msg.data["codconfitem"]});
        (async () => {
          await setItemReadyComboItems();
          renderListItemsCombo();
          
          setTimeout(function(){
            $(`.comboItemReadyCustomizable_component_list_items_item[data-codconf='${msg.data["codconfitem"]}']`).click();
          }, 1500);
        })();
      }

      Swal({
        type: "error",
        title: msg.msgTitle,
        html: msg.msg
      }); 
      return
    }

    Swal({
      type: "error",
      title: "Oops..",
      html: msg.msg,
    });
  }); 
}

function getQuantityItemCombo(codConf, itemId){
  if (!comboItemsEditing[codConf]) return 0;
  if (!comboItemsEditing[codConf]['items'][itemId]) return 0;

  return comboItemsEditing[codConf]['items'][itemId]['quantity'];
}

function setQuantityItemCombo(codConf, itemId, quantity, sizeId = null){
  if (!comboItemsEditing[codConf]) {
    comboItemsEditing[codConf] = {items: {}, total: 0};
    comboItemsEditing[codConf]['items'][itemId] = {
      quantity,
      sizeId
    };

    updateTotalComboItemsByCodConf(codConf);
    return;
  }

  if (!comboItemsEditing[codConf]['items'][itemId]) {
    comboItemsEditing[codConf]['items'][itemId] = {
      quantity,
      sizeId
    };

    updateTotalComboItemsByCodConf(codConf);
    return;
  }

  comboItemsEditing[codConf]['items'][itemId]['quantity'] = quantity;
  updateTotalComboItemsByCodConf(codConf);
}

function setQuantityItemCustomizableCombo(codConf, quantity, preReady = false, sizeId = null, flavors = null){
  if (!comboItemsEditing[codConf]) {
    comboItemsEditing[codConf] = {items: {}, total: 0, customizable: true, preReady, sizeId};
    comboItemsEditing[codConf]['items'][codConf] = {
      quantity,
      flavors
    };

    updateTotalComboItemsByCodConf(codConf);
    return;
  }

  if (!comboItemsEditing[codConf]['items'][codConf]) {
    comboItemsEditing[codConf]['items'][codConf] = {
      quantity,
      flavors
    };

    updateTotalComboItemsByCodConf(codConf);
    return;
  }

  comboItemsEditing[codConf]['items'][codConf]['quantity'] = quantity;
  updateTotalComboItemsByCodConf(codConf);
}

function updateTotalComboItemsByCodConf(codConf){
  let total = 0;

  if (comboItemsEditing[codConf]) {
    for (const item in comboItemsEditing[codConf]['items']) {
      total += parseInt(comboItemsEditing[codConf]['items'][item]['quantity']);
    }
  }

  comboItemsEditing[codConf]['total'] = parseInt(total);

  if (comboDataEditing['editing']['codigo']) {
    setComboItemsEditingStorage();
  }
  checkComboComplete();
}

function setComboItemsEditingStorage(){
  sessionStorage.setItem(`comboItemsEditing:${comboDataEditing['editing']['codigo']}`, JSON.stringify(comboItemsEditing));
}

function getTotalQuantityComboByCodConf(codConf){
  if (!comboItemsEditing[codConf]) return 0;

  return comboItemsEditing[codConf]['total'];
}

function checkComboComplete(finish = false){
  return new Promise((resolve, reject) => {
    const comboType = $('#comboType').val();
    let complete = true;
  
    for (const conf in comboDataEditing['default']) {
      const allowedQuantity = comboDataEditing['default'][conf]['allowedQuantity'];
      const total = getTotalQuantityComboByCodConf(conf);
      if (isNaN(total) || total < allowedQuantity) {
        complete = false;
        $(`.comboItem_quantity_value[data-combocodconf="${conf}"]`).css('opacity', '1');
        $(`.comboItem_quantity_value[data-combocodconf="${conf}"]`).attr('disabled', false);
        continue;
      };
  
      if (comboType == 'PADRAO' && finish && total > allowedQuantity) {
        complete = false;
        
        const msgQuantity = allowedQuantity == 1 ? 'unidade' : 'unidades';
        const sessionName = comboDataEditing['default'][conf]['sessionName'];
        
        Swal({
          type: 'info',
          title: 'Quantidade Não Permitida',
          text: `É possível adicionar apenas ${allowedQuantity} ${msgQuantity} de ${sessionName}`,
          onClose: () => {
            window.location.reload();
          }
        }); 
        reject('Item com quantidade não permitida');
        return;
      };
  
      Array.from($(`.comboItem_quantity_value[data-combocodconf="${conf}"]`)).forEach(x => {
        if ($(x).val() == 0) {
          $(x).css('opacity', '0.6');
          $(x).attr('disabled', true);
        }
      });
    }
  
    if (complete) {
      $('#btn_finalizar_combo').removeClass('btninativo');
      $('#btn_finalizar_combo').addClass('btnativo');
      if (isMobile) {
        window.scrollTo({ left: 0, top: document.body.scrollHeight, behavior: "smooth" });
      }
      resolve();
      return;
    }
  
    $('#btn_finalizar_combo').removeClass('btnativo');
    $('#btn_finalizar_combo').addClass('btninativo');
    resolve();
  })
}

function setComboReadyItems(){
  let comboItems = null;
  let comboItemsDb = isMobile ? JSON.parse($('#comboReadyItems').val()) : comboReadyItems; 
  const comboItemStorage = sessionStorage.getItem(`comboItemsEditing:${comboDataEditing['editing']['codigo']}`);
  if (comboItemStorage) {
    comboItems = JSON.parse(comboItemStorage);
  } else {
    comboItems = comboItemsDb;
  }

  for (const codConf in comboItems) {
    const items = comboItems[codConf]["items"];

    item:
    for (const itemId in items) {
      let inputNumber = $(`input[type="number"][data-combocodconf="${codConf}"][data-itemid="${itemId}"]`);
      if (items[itemId]['sizeId']) {
        inputNumber = $(`input[type="number"][data-combocodconf="${codConf}"][data-itemid="${itemId}"][data-sizeid="${items[itemId]['sizeId']}"]`);
      }
      if (inputNumber.length > 0) {
        inputNumber.val(items[itemId]['quantity']).change();
        continue item;
      }

      let inputRadio = $(`input[type="radio"][data-combocodconf="${codConf}"][value="${itemId}"]`);
      if (items[itemId]['sizeId']) {
        inputRadio = $(`input[type="radio"][data-combocodconf="${codConf}"][value="${itemId}"][data-sizeid="${items[itemId]['sizeId']}"]`);
      }
      if (inputRadio.length > 0) {
        inputRadio.click();
      }
    }
  }

  if (comboItemsDb) {
    for (const codConf in comboItemsDb) {
      if (comboItemsDb[codConf]['customizable']) {
        const preReady = comboItemsDb[codConf]['preReady'] ?? false;
        const sizeId = comboItemsDb[codConf]['sizeId'] ?? false;
        const flavors = comboItemsDb[codConf]['items'] ? Object.keys(comboItemsDb[codConf]['items']) : null;
        setQuantityItemCustomizableCombo(codConf, comboItemsDb[codConf]['total'], preReady, sizeId, flavors);
      }
    }
  }
}

function getHtmlDetailsItemCustomizableCombo(item){
  let htmDetails     = '';
 
  const flavors = item.sabores ?? null;
  const dough = item.item_massa ?? null;
  const edges = item.item_borda ?? null;
  const observations = item.item_observacoes ?? null;
  let compositions = item.item_compositions ?? null;
  const extraInfo = item.item_obs ?? null;

  if (flavors) {
    for (let i = 0; i < flavors.length; i++) {
      const flavorName = flavors[i]['item_sabornome'];
      const ingredientsAdd = flavors[i]['item_saboringredcom'] ?? [];
      const ingredientsRemoved = flavors[i]['item_saboringredrem'] ?? [];

      let listIngredients = '';
      for (let x = 0; x < ingredientsRemoved.length; x++) {
        listIngredients += `s/ ${ingredientsRemoved[x]['ingrediente_nome']}; `;
      }

      for (let x = 0; x < ingredientsAdd.length; x++) {
        const ingredientName = ingredientsAdd[x]['ingrediente_nome'];
        const ingredientQuantity = ingredientsAdd[x]['ingrediente_qtd'];

        if(ingredientQuantity && ingredientQuantity > 1) {
          listIngredients += `c/ ${ingredientQuantity}x ${ingredientName}; `;
        } else {
          listIngredients += "c/ "+ingredientName+"; ";
        }
      }

      if (listIngredients) {
        htmDetails += `<strong>${flavorName}: </strong> ${listIngredients}<br/>`;
      }
    }
  }
  
  if (dough) {
    const doughTypeName = dough['item_massanome'].split(":");
    const doughType = doughTypeName.length == 2 ? doughTypeName[0] : 'Massa';
    const doughName = doughTypeName.length == 2 ? doughTypeName[1] : dough['item_massanome'];
    htmDetails += `<strong>${doughType}: </strong> ${doughName}<br/>`;
  }
  
  if (edges) {
    let listEdges = '';
    const edgeTypeName = edges[0]['item_bordanome'].split(":");
    const edgeType = edgeTypeName.length == 2 ? edgeTypeName[0] : 'Borda';
    for (let i = 0; i < edges.length; i++) {
      const edgeNameType = edges[i]['item_bordanome'].split(":");
      let edgeName = edgeNameType[0];
      if (edgeNameType.length == 2) {
        edgeName = edgeNameType[1];
        listEdges += `${edgeName}; `;
      }
        
    }
    htmDetails += `<strong>${edgeType}: </strong> ${listEdges}<br/>`;
  }

  if (observations) {
    let listObs = '';
    for (let i = 0; i < observations.length; i++) {        
      listObs += `${observations[i]['item_observacaonome']}; `;            
    }
    htmDetails += `<strong>Observações: </strong> ${listObs}<br/>`;
  }

  if (compositions) {
    let categories = new Set();
    for (let i = 0; i < compositions.length; i++) {
      categories.add(compositions[i].categoryId);
    }

    categories = Array.from(categories);
    for (let i = 0; i < categories.length; i++) {
      let compositionsSession = compositions.filter(element => element['categoryId'] == categories[i]);

      let categoryName = compositionsSession[0]['categoryName'];
      let listCompositions = "";
      for (let x = 0; x < compositionsSession.length; x++) {
        listCompositions += ` ${compositionsSession[x]['amount']}x ${compositionsSession[x]['compositionName']};`;
      }

      htmDetails += `<strong>${categoryName}: </strong>${listCompositions}<br/>`;

      let compositionsAdd = item.item_compositionsAdd.filter(element => element['categoryId'] == categories[i]);
      if (compositionsAdd.length > 0) {
        let categoryNameAdd = compositionsAdd[0]['categoryName'];
        let listCompositionsAdd = "";
        for (let x = 0; x < compositionsAdd.length; x++) {
          listCompositionsAdd += ` ${compositionsAdd[x]['amount']}x ${compositionsAdd[x]['compositionName']};`;
        }

        htmDetails += `<strong>Adicional ${categoryNameAdd}: </strong>${listCompositionsAdd}<br/>`;
      }
    }
  }

  if (extraInfo) {
    htmDetails += `<strong>Obs. Cliente: </strong> ${extraInfo}<br/>`;
  }

  let html = '';
  if (htmDetails != '') {
    html = `
      <div class="comboDetailsItemCustomizable">
        <p>${htmDetails}</p>
      </div>
    `;
  }

  return html;
}

function removeItemCombo(orderComboId, configId, itemHash){
  const payload = {
    orderComboId: orderComboId,
    configComboId: configId,
    itemComboHash: itemHash
  }

  showLoading();               
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/removeitemcombo/",
    data: payload,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){
      if (typeof modalComboCurrent != "undefined" && modalComboCurrent) {
        (async () => {
          await removeItemReadyComboItems(configId);
          renderListItemsCombo();
        })()
        return;
      }

      document.location.reload();
      return;
    }

    Swal({
      type: "error",
      title: "Oops..",
      html: msg.msg,
    });
  }); 
}

function actionsCombo(data, action){
  const dataAction = {
    dados : data,
    acao : action
  };

  showLoading();
  $.ajax({
    method:"POST",
    url: "/exec/pedido/itemcombopedido/",
    data: dataAction,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){
      if(action === "editar"){
        if((typeof pgr != 'undefined' && pgr === true) || isMobile){
          document.location.href = msg.dados.redirect;
        } else if (isDesktopEddy) {
          msg.dados['comboStatus'] = 'editing';
          comboDataEditing['editing'] = msg.dados;
          openModalCombo(msg.dados)
        }
      } else if (isMobile && action === "deletar"){    
        showMensagem_baixo("Combo removido com sucesso.");           
      }
      get_resumoPedido();   
    } else {
      if (action == "editQuantity") {
        const comboId = data["skeyitem"];
        const quantityCurrent = $(`.inputQuantityComboSummary[data-id="${comboId}"]`).data('quantity-current');
        $(`.inputQuantityComboSummary[data-id="${comboId}"]`).val(quantityCurrent);
      }
      Swal({
        type: 'info',
        title: 'Combo Indisponível',
        text: msg.msg
      });
    }
  }).fail(function (data) {
    console.log('acoesComboPedido:fail: ', data);
    hideLoading();
    if(data.responseJSON.erro_msg != undefined){
      Swal({
        type: "error",
        title: "Oops..",
        html: data.responseJSON.erro_msg,
        onClose: () => {
          document.location.reload();
        }
      }); 
    }
  });
}

function openModalCombo(data){
  restartDataComboEditing();
  comboItems = data['items'];
  comboReadyItems = data['readyItems'];
  const comboData = {
    cod_resgate: data['cod_resgate'],
    fidelidade: data['fid'],
    data_hash: data['hash'],
    data_hascombo: data['hash'],
    data_cod: data['info']['combo_id']
  }

  comboDataEditing["editing"] = {
    codigo: data["orderComboId"] ?? null,
    hash: data["hash"] ?? null
  }

  const comboStatus = data['comboStatus'] ?? "new";
  modalComboCurrent = new ModalCombo(data['info']['combo_nome'], data['info']['combo_descricao'], data['info']['comboImageId'], data['info']['comboImageName'], comboData, comboStatus);
  setDataModalEddy(modalComboCurrent.getRender());
  openModalEddy();
  renderListItemsCombo();
  $('#modalEddy').addClass('modalCombo');
}

function restartDataComboEditing(){
  comboItems = [];
  comboReadyItems = [];
  currentComboItemQuantity = 0;
  comboDataEditing = {
    editing: {},
    default: {}
  };
  comboItemsEditing = {};
}

function renderEditorItemCombo(data){
  let typeEditor = data["options"]["typeEditor"];
  const nameEdge = listEdges.length > 0 ? listEdges[0]["borda_nome"].split(':')[0] : 'Borda';

  const isLoyalty = typeof modalComboCurrent != "undefined" ? modalComboCurrent.comboData["fidelidade"] : "N";
  if (isLoyalty == "S") {
    if (data["options"]["options"]["BORDAS"]["COBRAR"] == "S") {
      data["options"]["options"]["BORDAS"]["COBRAR"] = "N";
    }

    if (data["options"]["options"]["MASSA"]["COBRAR"] == "S") {
      data["options"]["options"]["MASSA"]["COBRAR"] = "N";
    }

    if (data["options"]["options"]["OBSERVASOES"]["COBRAR"] == "S") {
      data["options"]["options"]["OBSERVASOES"]["COBRAR"] = "N";
    }

    if (data["options"]["options"]["INGREDIENTE"]["COBRAR"] == "S") {
      data["options"]["options"]["INGREDIENTE"]["COBRAR"] = "N";
    }
  }

  let allowsManualObservationCombo = data["options"]?.allowsManualObservation == "S";

  if (typeEditor == "montarpizza" || typeEditor == "montarpizzaquadrada") {
    editorPizzaCurrent = new EditorPizza(typeEditor, data['itemrend'], data['hasitem'], nameEdge, '.component_modal_combo_items', allowsManualObservationCombo, "", data["options"]);
    editorPizzaCurrent.build();
  }

  if (!typeEditor || typeEditor == "montador-slider") {
    editorGenericCurrent = new EditorGeneric(data['itemrend'], data['hasitem'], nameEdge, '.component_modal_combo_items', allowsManualObservationCombo, "", data["options"]);
    editorGenericCurrent.build();
    $('.component_editor_generic_price').hide();
  }
}

function setItemReadyComboItems(){
  return new Promise((resolve, reject) => {
    const dataItem = getDataItem();
    let codConf = null;
    if (typeof editorPizzaCurrent !== "undefined" && editorPizzaCurrent) {
      codConf = editorPizzaCurrent.allowedOptions["codConf"];
    }

    if (typeof editorGenericCurrent !== "undefined" && editorGenericCurrent) {
      codConf = editorGenericCurrent.allowedOptions["codConf"];
    }
    
    let session = listSessions.find(x => x["sessao_id"] == dataItem["item_sessaoid"]);
    if (!session) {
      session = {sessao_nome: dataItem["item_sessaonome"], sessao_icone: ""}
    }
    const itemImageId = dataItem["sabores"].length == 1 ? dataItem["sabores"][0]["item_saborfotoid"] : null;
    const itemImageName = dataItem["sabores"].length == 1 ? dataItem["sabores"][0]["item_saborfotonome"] : `${urlsfiles["imagens"]}${session["sessao_icone"].slice(1)}`;
    const flavorsNames = [];
    for (let i = 0; i < dataItem["sabores"].length; i++) {
      flavorsNames.push(dataItem["sabores"][i]["item_sabornome"]);
    }

    for (let i = 0; i < comboItems.length; i++) {
      const codConfCombo = comboItems[i]["codConf"] ?? JSON.parse(comboItems[i]["comboData"])["data_codconfcombo"];
      if (codConfCombo == codConf) {
        const comboLink = $('#comboLink').val();
        const urlEditor = isDesktopEddy ? 'edit' : `/combo/${comboLink}/${comboDataEditing['editing']['codigo']}/item/${codConfCombo}/`
        comboItems[i] = {
          ...comboItems[i],
          type: "comboItemReadyCustomizable",
          sessionName: session["sessao_nome"],
          urlEditor: urlEditor,
          codConf: codConf,
          itemReady: [
            {
              "itemImageId": itemImageId,
              "itemImageName": itemImageName,
              "sizeName": dataItem["item_tamanhonome"],
              "itemFlavors": flavorsNames,
              "itemData": dataItem
            }
          ]
        }
        break;
      }
    }
  
    if (comboReadyItems.hasOwnProperty(codConf)) {
      comboReadyItems[codConf]["total"] = 1;
      resolve(true);
      return;
    }
  
    comboReadyItems[codConf] = {
      customizable: true,
      total: 1
    }
    resolve(true);
  })
}

function removeItemReadyComboItems(codConf){
  return new Promise((resolve, reject) => {  
    for (let i = 0; i < comboItems.length; i++) {
      if (comboItems[i]["codConf"] == codConf) {
        comboItems[i]["type"] = "comboItem";
        comboItems[i]["urlEditor"] = null;
        comboItems[i]["itemReady"] = null;
        break;
      }
    }
  
    if (comboReadyItems.hasOwnProperty(codConf)) {
      delete comboReadyItems[codConf];
    }

    setQuantityItemCombo(codConf, codConf, 0)
  
    resolve(true);
  })
}
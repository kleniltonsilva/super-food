let itemSettings = null;
let divisorCurrent = 1
let qtdEdgesAllowed = 1;
let itemEditing = {
  edges: [],
  dough: {},
  observations: [],
  ingredients: [],
}

let listFlavors = [];
let listSizes = [];
let listEdges = [];
let listDough = [];
let listIngredients = [];
let listObservations = [];
let listSessions = [];
let flavorEditing = {
  id: null,
  slice: null
}

$(document).ready(function () {
    if (typeof sabores_lista != "undefined") {
    listFlavors = sabores_lista;
  }

  if (typeof sabores_itens != "undefined") {
    listFlavors = sabores_itens;
  }

  if (typeof alltamanho != "undefined") {
    listSizes = alltamanho;
  }

  if (typeof tamanhos_lista != "undefined") {
    listSizes = tamanhos_lista;
  }

  if (typeof tamahos_itens != "undefined") {
    listSizes = tamahos_itens;
  }

  if (typeof bordas_lista != "undefined") {
    listEdges = bordas_lista;
  }

  if (typeof bordas_itens != "undefined") {
    listEdges = bordas_itens;
  }

  if (typeof massas_itens != "undefined") {
    listDough = massas_itens;
  }

  if (typeof massas_lista != "undefined") {
    listDough = massas_lista;
  }

  if (typeof observacoes_lista != "undefined") {
    listObservations = observacoes_lista;
  }

  if (typeof observacoes_itens != "undefined") {
    listObservations = observacoes_itens;
  }

  if (typeof observasoes_lista != "undefined") {
    listObservations = observasoes_lista;
  }

  if (typeof sessoes_itens != "undefined") {
    listSessions = sessoes_itens;
  }

  if (typeof sessao_item != "undefined") {
    listSessions = [sessao_item];
  }

  if (typeof ingredientes_itens != "undefined") {
    listIngredients = ingredientes_itens;
  }

  if ($("#itemSettings").length) {
    itemSettings = JSON.parse($("#itemSettings").val());
  }
  
  $(document).on("change", ".tamanho_itm", function (e) {
    const sizeId = $(this).val();
    const data = {
      tamanho: sizeId
    };
    const itemData = $("#cont_mont_lanche").data("dadosdoitematual");
    const action = "alterar";
    updateSize(itemData, data, action);
  });

  $(document).on("change", ".updateSize", function (e) {
    if ($(this).parent().hasClass("component_editor_pizza_buttons_actions")) {
      e.preventDefault();
      return;
    }

    if ($(this).parent().hasClass("component_editor_generic_div_select_sizes")) {
      e.preventDefault();
      return;
    }

    const sizeId = $(this).val();
    const data = {
      tamanho: sizeId
    };
    const itemData = $("#cont_mont_lanche").data("dadosdoitematual");
    const action = "alterar";
    updateSize(itemData, data, action);
  });

  $(document).on("change", ".selectqtditem", function (e) {
    const numberFlavors = $(this).val();
    const data = {
      qtdsabor: numberFlavors
    };

    const action = "alterar";
    const itemData = $("#cont_mont_lanche").data("dadosdoitematual");
    updateNumberFlavors(itemData, data, action);
  });


  $(document).on("click",".removeEdge",function(e){
    const edgeId = $(this).data("idborda");
    if (!edgeId) {
      openModalEdges();
      return;
    }
    
    itemEditing["edges"] = [];
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
    renderItemEdge();
    updateTotalItem();
  });

  $(document).on("click", ".removeObservations", function(e){
    const obsId = $(this).data("idobs");
    if (!obsId) {
      openModalObservations();
      return;
    }

    itemEditing["observations"] = [];
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
    renderItemObservations();
    updateTotalItem();
  });

  $(document).on("click",".openModalEdges", function(e){
    openModalEdges();
  });

  $(document).on("click",".openModalDough", function(e){
    openModalDough();
  });

  $(document).on("click",".openModalObservations", function(e){
    openModalObservations();
  });

  $(document).on("click",".openModalFlavors", function(e){    
    const slice = $(this).data('slice');
    flavorEditing["id"] = null;
    flavorEditing["slice"] = slice;

    openModalFlavors(slice);
  });

  $(document).on("change", ".modalEdges_selector_checkbox_input", function(e){
    $(this).parent().removeClass('is-focused');
    if ($('.modalEdges_selector_checkbox_input[type=checkbox]:checked').length > qtdEdgesAllowed) {
      $(this).prop('checked', false);
      $(this).parent().removeClass('is-checked');

      return;
    }
    updatePriceEdges();
  });

  $(document).on("change", ".modalEdges_selector_radio_input", function(e){
    updatePriceEdges();
  });

  $(document).on("click", ".modalEdges_selector_radio_input", function(e){
    if ($(this).hasClass("radio_checked")) {
      $(this).prop('checked', false);
      $(this).parent().removeClass('is-checked');
      $(this).removeClass('radio_checked');
      $(this).change();
      return;
    }

    $('.radio_checked').removeClass('radio_checked');
    $(this).addClass('radio_checked');
  });

  $(document).on("change", ".modalDough_selector_radio_input", function(e){
    updatePriceDough();
  });

  $(document).on("change", ".modalObservations_selector_checkbox_input", function(e){
    $(this).parent().removeClass('is-focused');
    updatePriceObservations();
  });

  $(document).on("change", ".modalIngredients_selector_checkbox_input", function(e){
    $(this).parent().removeClass('is-focused');
  });

  $(document).on("change", ".modalIngredientsAdd_selector_checkbox_input", function(e){  
    $(this).parent().removeClass('is-focused');  
    const max = $(this).data('max');

    let total = 0;
    const elements = Array.from($('.modalIngredientsAdd_selector_checkbox_input'));
    for (const element of elements) {
      if ($(element).is(':checked')) {
        total++;
      }
    }

    if (max > 0 && total > max) {
      $(this).prop('checked', false);
      $(this).parent().removeClass('is-checked');
      Swal({
        type: "warning",
        title: "Quantidade Inválida",
        html: `Não é possível adicionar mais que ${max} ingredientes para este tamanho!`
      }); 
      return;
    }

    updatePriceIngredientsAdd();
  });

  $(document).on("click", ".modalIngredientsAdd_quantity_decrease", function(e){    
    const ingredientId = $(this).data('itemid');
    const currentValue = parseInt($(`.modalIngredientsAdd_quantity_value[data-itemid="${ingredientId}"]`).val());

    if (currentValue == 0) return;

    $(`.modalIngredientsAdd_quantity_value[data-itemid="${ingredientId}"]`).val(currentValue - 1).change();
  });

  $(document).on("click", ".modalIngredientsAdd_quantity_increase", function(e){    
    const ingredientId = $(this).data('itemid');
    const currentValue = parseInt($(`.modalIngredientsAdd_quantity_value[data-itemid="${ingredientId}"]`).val());

    $(`.modalIngredientsAdd_quantity_value[data-itemid="${ingredientId}"]`).val(currentValue + 1).change();
  });

  $(document).on("change", ".modalIngredientsAdd_quantity_value", function(e){    
    const value = parseInt($(this).val());
    const max = parseInt($(this).data('max'));
    const maxPerIngredient = parseInt($(this).data('maxper'));

    let total = 0;
    const elements = Array.from($('.modalIngredientsAdd_quantity_value'));
    for (const element of elements) {
      total += parseInt($(element).val());
    }

    if (max > 0 && total > max) {
      $(this).val(max - (total - value)).change();
      
      Swal({
        type: "warning",
        title: "Quantidade Inválida",
        html: `Não é possível adicionar mais que ${max} ingredientes para este tamanho!`
      }); 
      return;
    }

    if (maxPerIngredient > 0 && value > maxPerIngredient) {
      $(this).val(maxPerIngredient).change();

      Swal({
        type: "warning",
        title: "Quantidade Inválida",
        html: `Não é possível adicionar mais que ${maxPerIngredient} de cada ingrediente!`
      });
      return;
    }

    updatePriceIngredientsAdd();
  });

  $(document).on("click", ".modalEdges_btnAddModalItem", function(e){
    setEdgesItemEditing();
    renderItemEdge();
    updateTotalItem();

    let modalTarget = '#';
    if ($('.component_editor_pizza_modalEddy').html() && $('.component_editor_pizza_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_pizza_';
    }

    if ($('.component_editor_generic_modalEddy').html() && $('.component_editor_generic_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_generic_';
    }
    closeModalEddy(modalTarget);
  });

  $(document).on("click", ".modalDough_btnAddModalItem", function(e){
    setDoughItemEditing();
    if (typeof editorPizzaCurrent !== "undefined" && editorPizzaCurrent) {
      editorPizzaCurrent.renderItemDough();
    }
    
    if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
      editorGenericCurrent.renderItemDough();
    }

    updateTotalItem();

    let modalTarget = '#';
    if ($('.component_editor_pizza_modalEddy').html() && $('.component_editor_pizza_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_pizza_';
    }

    if ($('.component_editor_generic_modalEddy').html() && $('.component_editor_generic_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_generic_';
    }

    closeModalEddy(modalTarget);
  });

  $(document).on("click", ".modalObservations_btnAddModalItem", function(e){
    setObservationsItemEditing();
    if (typeof editorPizzaCurrent !== "undefined" && editorPizzaCurrent) {
      editorPizzaCurrent.renderItemObservations();
    }
    
    if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
      editorGenericCurrent.renderItemObservations();
    }

    updateTotalItem();

    let modalTarget = '#';
    if ($('.component_editor_pizza_modalEddy').html() && $('.component_editor_pizza_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_pizza_';
    }

    if ($('.component_editor_generic_modalEddy').html() && $('.component_editor_generic_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_generic_';
    }
    
    closeModalEddy(modalTarget);
  });

  $(document).on("click", ".modalIngredients_btnAddModalItem", function(e){
    setIngredientsRemoveItemEditing();
    setIngredientsAddItemEditing();
    updateTotalItem();

    let modalTarget = '#';
    if ($('.component_editor_pizza_modalEddy').html() && $('.component_editor_pizza_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_pizza_';
    }

    if ($('.component_editor_generic_modalEddy').html() && $('.component_editor_generic_modalEddy').html().length > 0) {
      modalTarget = '.component_editor_generic_';
    }
    
    closeModalEddy(modalTarget);
  });
})

function updateSize(itemData, dataAction, action) {
  const data = {
    dadositem: itemData,
    dadosacao: dataAction,
    acao: action
  };
  showLoading();

  let bordaNome = 'Borda';
  let qtdBordasAntes = 0;
  if (itemData?.data_bordas && itemData.data_bordas != false) {
    qtdBordasAntes = itemData.data_bordas.length; //qtd bordas antes de trocar o tamanho
    if(itemData.data_bordas[0].item_bordanome != undefined && itemData.data_bordas[0].item_bordanome != false){
      bordaNome =  itemData.data_bordas[0].item_bordanome.substr(0, itemData.data_bordas[0].item_bordanome.indexOf(':')); 
    }
  }
  
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/tamanho/",
    data: data,
    dataType: "json"
  }).done(function (msg) {
    if (msg.res === true) {
      peencheDadosRetorno(msg);
      hideLoading();
      
      if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
        editorPizzaCurrent.updateDataItem(msg.item);
        editorPizzaCurrent.updateEditor();

        if (isMobile) {
          listIngredients = msg["ingredients"];
          listEdges = msg["edges"];
          listDough = msg["dough"];
          listObservations = msg["observations"];
          listFlavors = msg["flavors"];
          editorPizzaCurrent.setListEdges();
          editorPizzaCurrent.setListDough();
          editorPizzaCurrent.setListObservations();
          editorPizzaCurrent.setListFlavors();
          editorPizzaCurrent.setDough();
          editorPizzaCurrent.setEdges();
          editorPizzaCurrent.setObservations();
          editorPizzaCurrent.setIngredients();
          editorPizzaCurrent.renderFlavors();
          editorPizzaCurrent.renderItemEdge();
          editorPizzaCurrent.renderItemDough();
          editorPizzaCurrent.renderItemObservations();
        }
        return;
      }

      if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
        compositionsItemMontador["compositions"] = [];
        compositionsItemMontador["add"] = [];
        editorGenericCurrent.updateDataItem(msg.item);
        editorGenericCurrent.updateEditor();
        return;
      }

      $("#negative").trigger("click");
      
      let qtdBordasDepois = 0;
      if (msg.item.item_borda != undefined && msg.item.item_borda != false){
        qtdBordasDepois = msg.item.item_borda.length; //qtd bordas após a troca de tamanho
      }


      const itemInEditing = $('#itemInEditing').val();
      let sessionItemData = sessionStorage.getItem('itemEditingED');

      if (sessionItemData && itemInEditing) {
        sessionItemData = JSON.parse(sessionItemData);

        if (msg.item.item_massa) {
          const doughSplit = msg.item.item_massa["item_massanome"].split(':');
          const name = doughSplit.length > 1 ? doughSplit[1] : doughSplit[0];
          sessionItemData.dough = {
            id: msg.item.item_massa["item_massaid"],
            name,
            price: msg.item.item_massa["item_massapreco"]
          }
        }

        sessionItemData.edges = [];
        if (msg.item.item_borda) {
          for (const edge of msg.item.item_borda) {
            const edgeSplit = edge["item_bordanome"].split(':');
            const name = edgeSplit.length > 1 ? edgeSplit[1] : edgeSplit[0];
            sessionItemData.edges.push({
              id: edge["item_bordaid"],
              name,
              price: edge["item_bordapreco"]
            });
          }
        }

        sessionItemData.observations = [];
        if (msg.item.item_observacoes) {
          for (const observation of msg.item.item_observacoes) {
            const name = observation["item_observacaonome"]
            itemEditing.observations.push({
              id: observation["item_observacaoid"],
              name,
              price: observation["item_observacaopreco"]
            });
          }
        
        }

        sessionItemData.ingredients = [];
        if (msg.item.sabores.length > 0) {
          for (const flavor of msg.item.sabores) {
            const ingredientsAdd = [];
            const ingredientsRemove = [];

            if (flavor["item_saboringredrem"]) {
              for (const ingredient of flavor["item_saboringredrem"]) {
                ingredientsRemove.push({
                  id: ingredient["ingrediente_cod"]
                })
              }
            }

            if (flavor["item_saboringredcom"]) {
              for (const ingredient of flavor["item_saboringredcom"]) {
                ingredientsAdd.push({
                  id: ingredient["ingrediente_cod"],
                  quantity: ingredient["ingrediente_qtd"],
                  price: parseFloat(ingredient["ingrediente_preco"] / ingredient["ingrediente_qtd"]).toFixed(2)
                })
              }
            }

            itemEditing.ingredients.push({
              flavorId: flavor["item_saborid"],
              slice: flavor["item_saborpedaco"],
              ingredientsAdd,
              ingredientsRemove
            })
          }
        }

        sessionItemData["compositions"] = [];
        sessionItemData["compositionsAdd"] = [];

        itemEditing = sessionItemData;
        sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
      }

      if(qtdBordasAntes != qtdBordasDepois){
        //Verifica se as bordas foram removidas ao trocar para um tamanho que suportava menos qtd de bordas
        Swal({
          type: 'info',
          title: 'Atenção - ' + bordaNome + '(s) Removido(s)',
          html: 'O tamanho selecionado não permite essa quantidade de '+ bordaNome +'. Por favor, selecione novamente.',
          onClose: () => {
            if(redir_item === true){
              document.location.href = '/montar/'+link_sss+'/'+msg.item.item_cod;  
            }else{
              document.location.reload();
            }
          }
        });
      } else {
        if(msg.ing_add_removido && msg.ing_add_removido == true) {
          Swal({
            type: 'warning',
            title: 'Tamanho Alterado',
            html: 'Todos os ingredientes adicionais foram removidos. Por favor, adicione novamente.',
            onClose: () => {
              if(redir_item === true){
                document.location.href = '/montar/'+link_sss+'/'+msg.item.item_cod;  
              }else{
                document.location.reload();
              }
            }
          });
        } else {
          if(redir_item === true){
            document.location.href = '/montar/'+link_sss+'/'+msg.item.item_cod;  
          }else{
            document.location.reload();
          }
        }
      }
    } else if (msg.res === false) {
      hideLoading();
      $("#negative").trigger("click");

      editorUpdate();

      const type = msg["type"] ?? null;
      Swal({
        type: type || "error",
        title: "Oops..",
        html: msg.msg,
      }); 
    } else {
      setTimeout(function () {
        hideLoading();
      }, 2000);
    }
  });
}

function updateNumberFlavors(itemData, dataAction, action) {
  const data = {
    dadositem: itemData,
    dadosacao: dataAction,
    acao: action
  };
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/quantidadesabor/",
    data: data,
    dataType: "json"
  }).done(function (msg) {
    if (msg.res === true) {
      hideLoading();
      peencheDadosRetorno(msg);

      if (typeof itemEditing != "undefined") {
        const slices = new Set(msg.item["sabores"].map(x => parseInt(x["item_saborpedaco"])));
        itemEditing["ingredients"] = itemEditing["ingredients"].filter(x => slices.has(parseInt(x["slice"])));
      }

      if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
        editorPizzaCurrent.updateDataItem(msg.item);
        editorPizzaCurrent.updateEditor();
      } else if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
        editorGenericCurrent.updateDataItem(msg.item);
        editorGenericCurrent.updateEditor();
        return;
      } else if(redir_item === true){
        document.location.href = '/montar/'+link_sss+'/'+msg.item.item_cod;  
      }else{
        if(mtd === "mdl"){
          rendPizzaFormaPizza(msg.item);
          setTimeout(function () {
            hideLoading();
            $("#negative").trigger("click");
          }, 200);
        }else{
          document.location.reload();
        }
      }
    } else if (msg.res === false) {
      hideLoading();
      $("#negative").trigger("click");
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
    } else {
      setTimeout(function () {
        hideLoading();
      }, 2000);
    }
  });
}

function openModalEdges(){
  const list = getListEdges();
  const sessionId = getDataItem("sessionId");
  const sizeId = getDataItem("sizeId");
  const typeSortComplements = listSessions.find(x => x["sessao_id"] == sessionId)["sessao_tipoordenacaocomplementos"];
  let nameEdge = 'Borda';
  if (list.length > 0) {
    let name = list[0]['name'] ?? list[0]["borda_nome"];
    nameEdge = name.split(':')[0]; 
  }

  const quantityEdges = list[0]["sizeQuantityEdge"] ?? listSizes.find(x => x["tamanho_id"] == sizeId)["tamanho_qtdmaxborda"];
  const description = quantityEdges > 1 ? `Selecione até ${quantityEdges} opções` : 'Selecione 1 opção';
  const modal = new ModalItem("modalEdges", nameEdge, "", null, null, description);
  let modalTarget = "#";
  if ($('#modalEddy').html().length == 0) {
    modal.targetRender = "#modalEddy";
    modal.build();
    $('#modalEddy').addClass("modalEdges");
  } else {
    if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) {
      modal.targetRender = '.component_editor_pizza_modalEddy';
      modal.build();
      $('.component_editor_pizza_modalEddy').addClass("modalEdges");
      modalTarget = ".component_editor_pizza_";
    }

    if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) {
      modal.targetRender = '.component_editor_generic_modalEddy';
      modal.build();
      $('.component_editor_generic_modalEddy').addClass("modalEdges");
      modalTarget = ".component_editor_generic_";
    }
  }
  
  let edges = ordenaListaComplementos(typeSortComplements, list);
  edges = edges.map(x => {
    let name = x["name"] ?? x["borda_nome"];
    name = name.split(':')
    if (name.length > 1) {
      name = name[1];
    } else {
      name = name[0];
    }

    return {
      itemId: x["borda_id"],
      itemName: name,
      itemPrice: x["borda_preco"]
    }
  })

  const typeSelector = qtdEdgesAllowed > 1 ? "checkbox" : "radio";

  const edgesList = new ListItems("modalEdges", null, null, {typeSelector}, edges);
  $('.contentModalItem').append(edgesList.getRender());
  componentHandler.upgradeDom();

  showEdgesItem();
  openModalEddy(modalTarget);
}

function getItemsBySession(sessionId) {
  return new Promise((resolve, reject) => {
    showLoading();
  
    $.ajax({
      method: "GET",
      url: `/exec/menu/getItemsBySession?sessionId=${sessionId}`,
      dataType: "json",
      statusCode: {
        404: function() {
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: "Sem conexão com a internet.\nTente novamente mais tarde.",
            type: "error",
          }); 
          reject('Error 404');
        },
        500: function(response) {
          response = response['responseJSON'];
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: response.msg,
            type: "error",
          });
          reject('Error 500', response.msg);
        }
      }
    }).done(function (response) {
      hideLoading();
      if (response.res) {
        const { data } = response;
        resolve(data);
        return;
      } 
  
      Swal({
        type: "warning",
        title: "Ops! Algo deu Errado",
        html: response.msg,
      }); 
      reject(response.msg);
    });
  })
}

function getNewItem(sessionId){
  return new Promise((resolve, reject) => {
    $.ajax({
      method: "GET",
      url: `/exec/pedido/newItem?sessionId=${sessionId}`,
      dataType : "json",
      statusCode: {
        404: function() {
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: "Sem conexão com a internet.\nTente novamente mais tarde.",
            type: "error",
          }); 
          reject('Error 404');
        },
        500: function(response) {
          response = response['responseJSON'];
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: response.msg,
            type: "error",
          });
          reject('Error 500', response.msg);
        }
      }
    }).done(function( response ) {
      if(response.res === true){
        const { data } = response;
        resolve(data);
        return;
      }
      if(response.indisponibilidade_turno && response.indisponibilidade_turno == true && response.turnos_sessao && response.turnos_sessao.length > 0) {
        Swal({
          title: "Produto Indisponível",
          html: geraMensagemDisponibilidadePorTurno(response.turnos_sessao),
          type: "warning"                  
        }); 
        reject('turnos');
        return;
      }

      Swal({
        type: "warning",
        title: "Ops! Algo deu Errado",
        html: response.msg,
      }); 
    });
  })
}

function getItemEditing(itemId){
  return new Promise((resolve, reject) => {
    $.ajax({
      method: "GET",
      url: `/exec/pedido/getItemEditing?itemId=${itemId}`,
      dataType : "json",
      statusCode: {
        404: function() {
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: "Sem conexão com a internet.\nTente novamente mais tarde.",
            type: "error",
          }); 
          reject('Error 404');
        },
        500: function(response) {
          response = response['responseJSON'];
          hideLoading();
          Swal({
            title: "Ops! Algo deu Errado",
            html: response.msg,
            type: "error",
          });
          reject('Error 500', response.msg);
        }
      }
    }).done(function( response ) {
      if(response.res === true){
        const { data } = response;
        resolve(data);
        return;
      }

      if (response.redirect) {
        let editPathname = window.location.pathname.split('/');
        editPathname.pop();
        editPathname.pop();
        window.location.href = editPathname.join('/');
        return;
      }

      Swal({
        type: "warning",
        title: "Ops! Algo deu Errado",
        html: response.msg,
      }); 
    });
  })
}

function openModalIngredients(data, flavorName){
  const modal = new ModalItem("modalIngredients", flavorName.toUpperCase(), "", null, null, null, null, "Salvar");
  let modalTarget = "#";
  if ($('#modalEddy').html().length == 0) {
    modal.targetRender = "#modalEddy";
    modal.build();
    $('#modalEddy').addClass("modalIngredients");
  } else {
    if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) {
      modal.targetRender = '.component_editor_pizza_modalEddy';
      modal.build();
      $('.component_editor_pizza_modalEddy').addClass("modalIngredients");
      modalTarget = ".component_editor_pizza_";
    }

    if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) {
      modal.targetRender = '.component_editor_generic_modalEddy';
      modal.build();
      $('.component_editor_generic_modalEddy').addClass("modalIngredients");
      modalTarget = ".component_editor_generic_";
    }
  }

  const ingredients = data["ingredients"].map(x => {
    return {
      itemId: x["id"],
      itemName: x["name"]
    }
  })

  const allowsIngredientsRemove = getDataItem("allowsIngredientsRemove");
  const info = {
    typeSelector: allowsIngredientsRemove == "S" ? "checkbox" : null,
  }

  const ingredientsList = new ListItems("modalIngredients", null, null, info, ingredients);
  $('.contentModalItem').html(ingredientsList.getRender());
  showIngredients();

  const allowsIngredientsAdd = getDataItem("allowsIngredientsAdd");

  if (data["ingredientsAdd"].length > 0 && allowsIngredientsAdd == "S") {
    const ingredientsAdd = data["ingredientsAdd"].map(x => {
      return {
        itemId: x["id"],
        itemName: x["name"],
        itemPrice: x["price"]
      }
    })
  
    const maxIngredientAdd = getDataItem("maxIngredientAdd");
    const maxPerIngredientAdd = getDataItem("maxPerIngredientAdd");
    const typeSelector = maxIngredientAdd == 1 || maxPerIngredientAdd == 1 ? "checkbox" : "quantity";
    const info = {
      typeSelector,
      max: maxIngredientAdd,
      maxPer: maxPerIngredientAdd
    }

    const ingredientsAddList = new ListItems("modalIngredientsAdd", "Opcionais", null, info, ingredientsAdd);
    $('.contentModalItem').append(ingredientsAddList.getRender());
    showIngredientsAdd();
  }
  componentHandler.upgradeDom();

  openModalEddy(modalTarget);
}

function openModalObservations(){
  const list = getListObservations();
  const modal = new ModalItem("modalObservations", "Observações", "");
  let modalTarget = "#";
  if ($('#modalEddy').html().length == 0) {
    modal.targetRender = "#modalEddy";
    modal.build();
    $('#modalEddy').addClass("modalObservations");
  } else {
    if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) {
      modal.targetRender = '.component_editor_pizza_modalEddy';
      modal.build();
      $('.component_editor_pizza_modalEddy').addClass("modalObservations");
      modalTarget = ".component_editor_pizza_";
    }

    if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) {
      modal.targetRender = '.component_editor_generic_modalEddy';
      modal.build();
      $('.component_editor_generic_modalEddy').addClass("modalObservations");
      modalTarget = ".component_editor_generic_";
    }
  }

  const observations = list.map(x => {
    return {
      itemId: x["id"] ?? x["observacoes_id"],
      itemName: x["name"] ?? x["observacoes_nome"],
      itemPrice: x["price"] ?? x["observacoes_preco"]
    }
  })

  const observationsList = new ListItems("modalObservations", null, null, null, observations);
  $('.contentModalItem').html(observationsList.getRender());
  componentHandler.upgradeDom();

  showObservationsItem();
  openModalEddy(modalTarget);
}

function openModalDough(){  
  const list = getListDough();
  let nameDough = 'Massa';
  if (list.length > 0) {
    let name = list[0]['name'] ?? list[0]["massa_nome"];
    nameDough = name.split(':')[0]; 
  }
    
  const modal = new ModalItem("modalDough", nameDough, "");
  let modalTarget = "#";
  if ($('#modalEddy').html().length == 0) {
    modal.targetRender = "#modalEddy";
    modal.build();
    $('#modalEddy').addClass("modalDough");
  } else {
    if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) {
      modal.targetRender = '.component_editor_pizza_modalEddy';
      modal.build();
      $('.component_editor_pizza_modalEddy').addClass("modalDough");
      modalTarget = ".component_editor_pizza_";
    }

    if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) {
      modal.targetRender = '.component_editor_generic_modalEddy';
      modal.build();
      $('.component_editor_generic_modalEddy').addClass("modalDough");
      modalTarget = ".component_editor_generic_";
    }
  }
  
  const dough = list.map(x => {
    let name = x["name"] ?? x["massa_nome"];
    name = name.split(':');
    if (name.length > 1) {
      name = name[1];
    } else {
      name = name[0];
    }

    return {
      itemId: x["id"] ?? x["massa_id"],
      itemName: name,
      itemPrice: x["price"] ?? x["massa_preco"]
    }
  })

  const doughList = new ListItems("modalDough", null, null, null, dough);
  $('.contentModalItem').html(doughList.getRender());
  componentHandler.upgradeDom();

  showDoughItem();
  openModalEddy(modalTarget);
}

function openModalFlavors(){
  const modal = new ModalItem("modalFlavors", "Selecione um Sabor", "");
  let modalTarget = "#";
  if ($('#modalEddy').html().length == 0) {
    modal.targetRender = "#modalEddy";
    modal.build();
    $('#modalEddy').addClass("modalFlavors");
  } else {
    if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) {
      editorPizzaCurrent.showHand = false;
      modal.targetRender = '.component_editor_pizza_modalEddy';
      modal.build();
      $('.component_editor_pizza_modalEddy').addClass("modalFlavors");
      modalTarget = ".component_editor_pizza_";
    }

    if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) {
      editorGenericCurrent.showHand = false;
      modal.targetRender = '.component_editor_generic_modalEddy';
      modal.build();
      $('.component_editor_generic_modalEddy').addClass("modalFlavors");
      modalTarget = ".component_editor_generic_";
    }
  }

  const list = getListFlavors();
  
  if (!list.length) return;
  
  const listFlavors = ordenaListaProdutoComposto(list[0].sessao_tipoordenacao, list);
  
  const quantityFlavorsItem = getDataItem("quantityFlavorsItem");
  const sizeId = getDataItem("sizeId");

  const listFlavorsByCategory = {}
  for (let i = 0; i < listFlavors.length; i++) {
    const category = listFlavors[i]["sabor_categorianome"];
    if (!listFlavorsByCategory[category]) {
      listFlavorsByCategory[category] = [];
    }

    if (listFlavors[i]?.sabor_precostamanhos) {
      const getSize = listFlavors[i].sabor_precostamanhos.find(x => x["sabor_precotamanhos_codtamanho"] == sizeId);
      if (!getSize) continue;
      const sizeData = {};
      for (const key in getSize) {
        sizeData[key.replace("precotamanhos_", "")] = getSize[key];
      }

      let priceOrigin = sizeData["sabor_preco"];
      let pricePromo = sizeData["sabor_precopromo"];

      if(sizeData[`sabor_precofixo${quantityFlavorsItem}sabor`]){
        let price = sizeData[`sabor_precofixo${quantityFlavorsItem}sabor`];
        let priceSizePromo = sizeData[`sabor_precofixo${quantityFlavorsItem}saborpromo`];
        if (price > 0) {
          priceOrigin = parseFloat(price);
          pricePromo = parseFloat(priceSizePromo);
        }
      }

      sizeData["sabor_preco"] = priceOrigin;
      sizeData["sabor_precopromo"] = pricePromo;

      listFlavors[i] = {
        ...listFlavors[i],
        ...sizeData
      };
    }

    listFlavorsByCategory[category].push(listFlavors[i]);
  }

  for (const category in listFlavorsByCategory) {
    const flavors = listFlavorsByCategory[category];
    if (flavors.length == 0) continue;
    
    const categoryList = new ListItems("modalFlavors", flavors[0]["sabor_categorianome"], null, null, flavors);
    $('.contentModalItem').append(categoryList.getRender());
  }

  $('#maozinha').hide();
  efeitomaozinha = false;

  $( ".modalFlavors_component_list_items_item" ).on( "click", function(e) {
    setFlavor(getDataItemCurrent(), $(this).data('modalflavors-itemid'), flavorEditing["slice"]);
  });

  openModalEddy(modalTarget);
}

function setEdgesItemEditing(){
  itemEditing['edges'] = [];
  Array.from($('.modalEdges_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      itemEditing['edges'].push({
        id: $(x).val(),
        name: $(x).data("name"),
        price: $(x).data("price")
      });
    }
  });

  Array.from($('.modalEdges_selector_radio_input')).map(x => {
    if ($(x).is(':checked')) {
      itemEditing['edges'].push({
        id: $(x).val(),
        name: $(x).data("name"),
        price: $(x).data("price")
      });
    }
  });

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function setDoughItemEditing(){
  const dough = $('.modalDough_selector_radio_input:checked');
  if (dough.length == 0) return;

  itemEditing.dough = {
    id: dough.val(),
    name: dough.data("name"),
    price: dough.data("price")
  }

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function setObservationsItemEditing(){
  itemEditing['observations'] = [];
  Array.from($('.modalObservations_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      itemEditing['observations'].push({
        id: $(x).val(),
        name: $(x).data("name"),
        price: $(x).data("price")
      });
    }
  });

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function setIngredientsRemoveItemEditing(){
  let index = null;
  for (let i = 0; i < itemEditing["ingredients"].length; i++) {
    if (itemEditing["ingredients"][i]["slice"] == flavorEditing["slice"]) {
      itemEditing["ingredients"][i]["ingredientsRemove"] = [];
      index = i;
    }
  }

  let dataUpdate = [];
  Array.from($('.modalIngredients_selector_checkbox_input')).map(x => {
    if (!$(x).is(':checked')) {
      dataUpdate.push({
        id: $(x).val(),
        name: $(x).data("name")
      });
    }
  });

  if (index != null) {
    itemEditing["ingredients"][index]["ingredientsRemove"] = dataUpdate;
  } else {
    itemEditing["ingredients"].push({
      flavorId: flavorEditing["id"],
      slice: flavorEditing["slice"],
      ingredientsRemove: dataUpdate,
      ingredientsAdd: []
    })
  }

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function setIngredientsAddItemEditing(){
  let index = null;
  for (let i = 0; i < itemEditing["ingredients"].length; i++) {
    if (itemEditing["ingredients"][i]["slice"] == flavorEditing["slice"]) {
      itemEditing["ingredients"][i]["ingredientsAdd"] = [];
      index = i;
    }
  }

  let dataUpdate = [];
  Array.from($('.modalIngredientsAdd_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      dataUpdate.push({
        id: $(x).val(),
        name: $(x).data("name"),
        price: $(x).data("price") || 0,
        quantity: 1
      });
    }
  });

  Array.from($('.modalIngredientsAdd_quantity_value')).map(x => {
    if ($(x).val() > 0) {
      dataUpdate.push({
        id: $(x).data("itemid"),
        name: $(x).data("name"),
        price: $(x).data("price") || 0,
        quantity: $(x).val()
      });
    }
  });

  if (index != null) {
    itemEditing["ingredients"][index]["ingredientsAdd"] = dataUpdate;
  } else {
    itemEditing["ingredients"].push({
      flavorId: flavorEditing["id"],
      slice: flavorEditing["slice"],
      ingredientsAdd: dataUpdate,
      ingredientsRemove: []
    })
  }

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function showEdgesItem(){
  const edges = itemEditing['edges'];
  if (edges.length == 0) return;

  for (edge of edges) {
    const element = $(`.modalEdges_selector_checkbox_input[value="${edge["id"]}"]`);
    if (element.length > 0) {
      element.click();
    } else {
      const elementRadio = $(`.modalEdges_selector_radio_input[value="${edge["id"]}"]`);
      if (elementRadio.length > 0) {
        elementRadio.click();
      } 
    }
  }
}

function showDoughItem(){
  const dough = itemEditing['dough'];
  if (dough.length == 0) return;

  const element = $(`.modalDough_selector_radio_input[value="${dough["id"]}"]`);
  if (element.length > 0) element.click();
}

function showIngredients(){
  const dataFlavor = itemEditing["ingredients"].find(x => parseInt(x["slice"]) == parseInt(flavorEditing["slice"]));
  const ingredients = dataFlavor ? dataFlavor['ingredientsRemove'] : [];

  $('.modalIngredients_selector_checkbox_input').click();
  if (ingredients.length == 0) return;

  for (const ingredientId of ingredients) {
    const element = $(`.modalIngredients_selector_checkbox_input[value="${ingredientId["id"]}"]`);
    if (element.length > 0) element.click();
  }
}

function showIngredientsAdd(){
  const dataFlavor = itemEditing["ingredients"].find(x => parseInt(x["slice"]) == parseFloat(flavorEditing["slice"]));
  const ingredients = dataFlavor ? dataFlavor['ingredientsAdd'] : [];
  if (ingredients.length == 0) return;

  for (const ingredient of ingredients) {
    let element = $(`.modalIngredientsAdd_selector_checkbox_input[value="${ingredient["id"]}"]`);
    if (element.length > 0) {
      element.click();
      continue;
    }

    element = $(`.modalIngredientsAdd_quantity_value[data-itemid="${ingredient["id"]}"]`);
    if (element.length > 0) {
      element.val(ingredient["quantity"]);
      element.change();
    }
  }
}

function showObservationsItem(){
  const observations = itemEditing['observations'];
  if (observations.length == 0) return;

  for (edge of observations) {
    const element = $(`.modalObservations_selector_checkbox_input[value="${edge["id"]}"]`);
    if (element.length > 0) element.click();
  }
}

function updatePriceEdges(){
  const typeCalculation = getDataItem("typeCalculationEdges");

  let total = 0;
  let quantity = 0;
  Array.from($('.modalEdges_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      quantity++;
      const value = parseFloat($(x).data('price'));
      if (typeCalculation == "MAIOR") {
        total = value > total ? value : total;
      } else {
        total = total + parseFloat($(x).data('price'));
      }
    }
  });

  Array.from($('.modalEdges_selector_radio_input')).map(x => {
    if ($(x).is(':checked')) {
      quantity++;
      const value = parseFloat($(x).data('price'));
      if (typeCalculation == "MAIOR") {
        total = value > total ? value : total;
      } else {
        total = total + parseFloat($(x).data('price'));
      }
    }
  });

  if (typeCalculation == "MEDIA") {
    total = total / quantity;
  }

  $('#modalEdges_price').html(`R$ ${parseReal(total)}`);
}

function updatePriceDough(){
  let total = 0;
  let price = $('.modalDough_selector_radio_input:checked').data('price');
  if (price) {
    total = parseFloat(price);
  }

  $('#modalDough_price').html(`R$ ${parseReal(total)}`);
}

function updatePriceObservations(){
  let total = 0;
  Array.from($('.modalObservations_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      total = total + parseFloat($(x).data('price'));
    }
  });

  $('#modalObservations_price').html(`R$ ${parseReal(total)}`);
}

function updatePriceIngredientsAdd(){
  let total = 0;

  const ingredients = [];
  Array.from($('.modalIngredientsAdd_selector_checkbox_input')).map(x => {
    if ($(x).is(':checked')) {
      ingredients.push({quantity: 1, price: parseFloat($(x).data('price'))});
    }
  });

  Array.from($('.modalIngredientsAdd_quantity_value')).map(x => {
    if ($(x).val() > 0) {
      ingredients.push({quantity: $(x).val(), price: parseFloat($(x).data('price'))});
    }
  });

  const typeCalculationIngredients = getDataItem("typeCalculationIngredients");

  if (typeCalculationIngredients == "MAIOR") {
    total = ingredients.reduce((max, ingredient) =>  max > (ingredient.price * ingredient.quantity) ? max : ingredient.price * ingredient.quantity, 0);
  } else {
    total = ingredients.reduce((acc, ingredient) => acc + ingredient.price * ingredient.quantity, 0);
  }

  if (typeCalculationIngredients == "MEDIA" && ingredients.length > 0) {
    total = total / ingredients.length;
  }

  $('#modalIngredients_price').html(`R$ ${parseReal(total)}`);
}

function setDataItemEditing(){
  const itemInEditing = $('#itemInEditing').val();
  let sessionItemData = sessionStorage.getItem('itemEditingED');
  if (sessionItemData && itemInEditing) {
    sessionItemData = JSON.parse(sessionItemData);
    itemEditing = sessionItemData;
    return;
  }
  
  sessionStorage.removeItem('itemEditingED');
  const itemData = $("#cont_mont_lanche").data("dadositem");
  if (!itemData) return;
  
  if (itemData["item_massa"] && typeof itemData["item_massa"] == 'object') itemEditing.dough = { 
    id: itemData["item_massa"]["item_massaid"], 
    name: itemData["item_massa"]["item_massanome"].replace(`${nomemassa}:`, ''),
    price: itemData["item_massa"]["item_massapreco"]
  };
  if (itemData["item_borda"] && Array.isArray(itemData["item_borda"])) itemEditing.edges = itemData["item_borda"].map(x => {
    return {
      id: x["item_bordaid"],
      name: x["item_bordanome"].replace(`${nomeborda}:`, ''),
      price: x["item_bordapreco"]
    }
  });
  if (itemData["item_observacoes"] && Array.isArray(itemData["item_observacoes"])) itemEditing.observations = itemData["item_observacoes"].map(x => {
    return {
      id: x["item_observacaoid"],
      name: x["item_observacaonome"],
      price: x["item_observacaopreco"]
    }
  });

  itemEditing.ingredients = [];
  if (itemData["sabores"].length > 0) {
    for (const flavor of itemData["sabores"]) {
      const ingredientsAdd = [];
      const ingredientsRemove = [];

      if (flavor["item_saboringredrem"]) {
        for (const ingredient of flavor["item_saboringredrem"]) {
          ingredientsRemove.push({
            id: ingredient["ingrediente_cod"]
          })
        }
      }

      if (flavor["item_saboringredcom"]) {
        for (const ingredient of flavor["item_saboringredcom"]) {
          ingredientsAdd.push({
            id: ingredient["ingrediente_cod"],
            quantity: ingredient["ingrediente_qtd"],
            price: ingredient["ingrediente_preco"]
          })
        }
      }

      itemEditing.ingredients.push({
        flavorId: flavor["item_saborid"],
        slice: flavor["item_saborpedaco"],
        ingredientsAdd,
        ingredientsRemove
      })
    }
  }

  sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
}

function updateTotalItem(){
  const typeCalculationEdges = getDataItem("typeCalculationEdges");
  const typeCalculationIngredients = getDataItem("typeCalculationIngredients");
  const flavorsPrice = getDataItem("flavorsPrice");

  let compositionsPrice = 0;
  if (typeof pricesCompositions != 'undefined') {
    for (const key in pricesCompositions) {
      compositionsPrice += pricesCompositions[key];
    }
  
    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;
  
    compositionsPrice = compositionsPrice * qtdItem;
  }

  let total = itemSettings ? 0 : parseFloat(flavorsPrice);
  total = total + parseFloat(compositionsPrice);

  if (itemEditing["ingredients"].length > 0) {
    const allIngredientsAdd = [];
    for (const getIngredients of itemEditing["ingredients"]) allIngredientsAdd.push(...getIngredients["ingredientsAdd"]);
    total = total + (() => {
      let value = 0;

      if (typeCalculationIngredients == "MAIOR") {
        value = allIngredientsAdd.reduce((max, ingredient) => max > parseFloat(ingredient.price) * ingredient.quantity ? max : parseFloat(ingredient.price) * ingredient.quantity, 0);
      } else {
        value = allIngredientsAdd.reduce((acc, ingredient) => acc + parseFloat(ingredient.price) * ingredient.quantity, 0);
      }
  
      const quantityIngredientsAdd = allIngredientsAdd.length;
      if (typeCalculationIngredients == "MEDIA" && quantityIngredientsAdd > 0) {
        value = value / allIngredientsAdd.length;
      }
  
      return value;
    })();
  }

  total = total + parseFloat(itemEditing.dough.price || 0);
  total = total + itemEditing.observations.reduce((acc, observations) => acc + (observations.price ? parseFloat(observations.price) : 0), 0);
  total = total + (() => {
    let value = 0;
    if (typeCalculationEdges == "MAIOR") {
      value = itemEditing.edges.reduce((max, edge) => max > (edge.price ? parseFloat(edge.price) : 0) ? max : (edge.price ? parseFloat(edge.price) : 0), 0);
    } else {
      value = itemEditing.edges.reduce((acc, edge) => acc + (edge.price ? parseFloat(edge.price) : 0), 0);
    }

    const quantityEdges = itemEditing.edges.length;
    if (typeCalculationEdges == "MEDIA" && quantityEdges > 0) {
      value = value / itemEditing.edges.length;
    }

    return value;
  })();

  $('#precodonome').html(`R$ ${parseReal(total)}`);
  $('.preco_item_lanche').html(`R$ ${parseReal(total)}`);
  $('.total_pizza').html(`Preço da pizza: R$ ${parseReal(total)}`);
  $('.tota_price_item').html(`Preço da pizza: R$ ${parseReal(total)}`);

  let amount = $('.modalAddItem_quantity_value');
  if (amount.length > 0) {
    amount = parseInt(amount.val());
  } else {
    amount = 1;
  }

  $('#modalAddItem_price').html(`R$ ${parseReal((total * amount) / divisorCurrent)}`);
}

function renderItemEdge(){
  const nameEdge = listEdges.length > 0 ? listEdges[0]["borda_nome"].split(':')[0] : 'Borda';
  if ($("#areabordas").length == 0) return;

  const list = typeof editorPizzaCurrent != "undefined" ? editorPizzaCurrent.edges : listEdges;
  if (!list || list.length == 0) {
    $('#pizzaEdges').hide();
    return;
  }

  let htmlEdges = "";
  const edges = itemEditing.edges;
  if (edges.length == 0) {
    $('#pizzaEdges').show();
    $("#areabordas").html('');
    return;
  }

  let onlyEdge = edges.length == 1 ? edges[0].id : "";
  htmlEdges = `
    <span class='lblsabor'>
      <span class='removeEdge' data-idborda="${onlyEdge}" title='Excluir Bordas'>
        <i class='material-icons'>cancel</i>
      </span>`;

  let textEdgesName = `${nameEdge}: `;
  for(let fd = 0; fd < edges.length; fd++){
    const edgeName = edges[fd].name;
    textEdgesName += edgeName + ", ";
  }

  textEdgesName = textEdgesName.slice(0, -2);
  htmlEdges += `
    <a class='lbldesc openModalEdges descriptionEditEdges' title='Bordas'><div class="descriptionEdges">${textEdgesName}</div><i class='material-icons'>edit</i></a>
  </span>`;

  $('#pizzaEdges').hide();
  $("#areabordas").html(htmlEdges);
}

function renderItemObservations(){
  if ($("#areaobservacoes").length == 0) return;

  const list = typeof editorPizzaCurrent != "undefined" ? editorPizzaCurrent.observations : listObservations;
  if (!list || list.length == 0) {
    $('#pizzaObservations').hide();
    return;
  }

  let htmlObs = "";
  const observations = itemEditing["observations"];
  if (observations.length == 0) {
    $('#pizzaObservations').show();
    $("#areaobservacoes").html('');
    return;
  }
  
  let onlyObservation = observations.length == 1 ? observations[0].id : "";
  htmlObs = `
    <span class='lblsabor'>
      <span class='del-borda del-obs removeObservations' title='Excluir observação' data-idobs='${onlyObservation}'>
        <i class='material-icons'>cancel</i>
      </span>`;
    
  let textObservationsName = "";
  for (let fd = 0; fd < observations.length; fd++) {
    let observationName = observations[fd].name;
    textObservationsName += observationName + ", ";
  }

  textObservationsName = textObservationsName.slice(0, -2);
  htmlObs += `
    <a class='lbldesc openModalObservations descriptionEditObservations' title='Observações'><div class="descriptionObservations">${textObservationsName}</div><i class='material-icons'>edit</i></a>
  </span>`;
      
  $('#pizzaObservations').hide();
  $("#areaobservacoes").html(htmlObs);
}

function renderItemDough(){
  const list = typeof editorPizzaCurrent != "undefined" ? editorPizzaCurrent.dough : listDough;
  if (!list || list.length == 0) return;

  let nameDough = "Massa";
  if (list.length > 0) {
    nameDough = list[0]["name"] ? list[0]["name"].split(':')[0] : list[0]["massa_nome"].split(':')[0];
  }

  let html = "";
  const dough = itemEditing.dough;
  if(dough != undefined && dough != false && $("#areamassa").length > 0){
    html = "<span class='lblsabor'>"
    +    "<span class='removeDough' title='Alterar "+nameDough+"'><i class='material-icons'>cancel</i></span>"
    +    "<a class='lbldescopt openModalDough descriptionEditEdges' title='"+dough.name+"'><div class='descriptionDough'>"+ nameDough + ': ' + dough.name+"</div><i class='material-icons'>edit</i></a>"
    +"</span>";
  }
  
  const getDough = typeof list != "undefined" ? list.find(x => (x["id"] ?? x["massa_id"]) == dough["id"]) : null;
  if (getDough && getDough['allowsEdge'] == "N") {
    itemEditing.edges = [];
    renderItemEdge();
    $('#pizzaEdges').hide();
  } else {
    const edges = typeof editorPizzaCurrent != "undefined" ? editorPizzaCurrent.edges : listEdges;
    if (itemEditing.edges.length == 0 && edges.length > 0) {
      $('#pizzaEdges').show();
    }
  }
  
  $("#areamassa").html(html);
}

function setConfigItem(){
  const itemData = getDataItem();
  if (!itemData) return;
  itemPriceCurrent = itemData["item_flavorsprice"];
  const sizeId = itemData["item_tamanhoid"];
  const sizes = listSizes;
  const getSize = sizes.find(x => x['tamanho_id'] == sizeId);
  if (getSize) {
    qtdEdgesAllowed = getSize["QTD_BORDA"] ?? getSize["tamanho_qtdmaxborda"];
  }
  itemEditing.edges = itemEditing.edges.slice(0, qtdEdgesAllowed);
}

function removeFlavor(itemData, flavorId, slice){
  const dataAction = {
    data_sabor : flavorId,
    data_pedaco : slice
  };

  const dados = {
    dadositem : itemData,
    dadosacao : dataAction,
    acao : "remover"
  };

  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/sabores/",
    data: dados,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){
      peencheDadosRetorno(msg);
      
      if (typeof itemEditing != "undefined") {
        itemEditing["ingredients"] = itemEditing["ingredients"].filter(x => x["slice"] != slice);
      }

      if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
        editorPizzaCurrent.updateDataItem(msg.item);
        editorPizzaCurrent.updateEditor();
        return;
      }

      if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
        editorGenericCurrent.updateDataItem(msg.item);
        editorGenericCurrent.updateEditor();
        return;
      }
    }
  }); 
}

function setFlavor(dataItem, flavor, slice){
  const dataAction = {
    data_sabor : flavor,
    data_pedaco : slice
  };
  
  const dados = {
    dadositem : dataItem,
    dadosacao : dataAction,
    acao : "adicionar"
  };

  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/sabores/",
    data: dados,
    dataType: "json"
  }).done(function( msg ) {
    hideLoading();
    if(msg.res === true){
      $("#negative").trigger("click");
      peencheDadosRetorno(msg);
      editorUpdateDataItem(msg.item);
      editorUpdate();

      if (isMobile) $('.backdrop').click();
    }else if(msg.res === false){
      Swal({
        type: "error",
        title: 'Ocorreu um erro',
        html: msg.msg,
        onClose: () => {
          window.location.reload();
        }                
      }); 
      return;
    }
  }); 
}

function startDataItem(){
  setDataItemEditing();
  setConfigItem();

  renderItemEdge();
  renderItemDough();
  renderItemObservations();
  renderItemCompositions();

  updateTotalItem();
}

async function renderItemCompositions(){
  const compositions = typeof editorSliderCurrent != "undefined" && editorSliderCurrent ? editorSliderCurrent["dataItem"]["item_compositions"] : compositionsItemMontador["compositions"];
  const compositionsAdd = typeof editorSliderCurrent != "undefined" && editorSliderCurrent ? editorSliderCurrent["dataItem"]["item_compositionsAdd"] : compositionsItemMontador["add"];

  if (compositions) {
    for (const composition of compositions) {
      const id = composition["compositionId"];
      const quantity = composition["amount"];

      if (quantity == 0) continue;

      if ($(`#list-compositionid-${id}`).length > 0) {
        $(`#list-compositionid-${id}`).click();
        continue;
      }

      const input = $(`.inputComposition[data-compositionid="${id}"]`);
      if (input.length > 0) {
        input.val(quantity).change();
      }
    }
  }

  if (compositionsAdd) {
    for (const composition of compositionsAdd) {
      const id = composition["compositionId"];
      const categoryId = composition["categoryId"] ?? composition["catCompositionId"];
      const quantity = parseInt(composition["amount"]);

      if (quantity == 0) continue;

      if ($(`.toggle_compositions[data-catcompositionid="${categoryId}"]`).find('i').text() == 'keyboard_arrow_up') {
        $(`.toggle_compositions[data-catcompositionid="${categoryId}"]`).click();
      }

      if ($(`#add-list-compositionid-${id}`).length > 0) {
        $(`#add-list-compositionid-${id}`).click();
        continue;
      }

      const input = $(`.inputCompositionAdd[data-compositionid="${id}"]`);
      if (input.length > 0) {
        input.val(quantity).change();
      }
    }
  }
}

function getDataItem(data = null){
  let source = null;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) source = editorPizzaCurrent["dataItem"];
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) source = editorGenericCurrent["dataItem"];
  if (typeof editorSliderCurrent != "undefined" && editorSliderCurrent) source = editorSliderCurrent["dataItem"];
  if (!source) source = $("#cont_mont_lanche").data("dadositem");
  if (!source) source = {};
  
  switch (data) {
    case "allowsIngredientsAdd":
      return source["item_sessao_addingredientes"];
    case "allowsIngredientsRemove":
      return source["item_sessao_removeringredientes"];
    case "maxIngredientAdd":
      return source["item_qtd_max_ingred_adicionais"];
    case "maxPerIngredientAdd":
      return source["item_qtd_max_por_ingred_adicionais"];
    case "typeCalculationEdges":
      return source["item_formaCalculoOpcionais"] ?? source["sessao_formaCalculoOpcionais"];
    case "typeCalculationIngredients":
      return source["item_formaCalculoIngrediente"] ?? source["sessao_formaCalculoIngrediente"];
    case "typeCalculationIngredientsPerSlice":
      if (source["sabores"] && source["sabores"].length > 1) {
        return source["item_fracionarIngrediente"] && source["item_fracionarIngrediente"] == "FRACAO" ? "MEDIA" : "SOMA"
      }

      return "SOMA";
    case "flavorsPrice":
      if (typeof itemPriceCurrent != "undefined") return itemPriceCurrent;
      return source["item_flavorsprice"];
    case "sessionId":
      return source["item_sessaoid"] ?? source["sabor_sessaoid"];
    case "sizeId":
      if (typeof itemSizeId != "undefined") return itemSizeId;  
      return source["item_tamanhoid"] ?? item_tamanho;
    case "quantityFlavorsItem":
      return source["item_qtdsabor"];
    default: 
      return source;
  }
}

function addCustomItem(dataItem, detalhes, urlredir) {
  if (finalizaItemAndamento) {
    console.error('finalizaPedidoAndamento');
    return;
  }

  finalizaItemAndamento = true;

  const data = {
    dadositem: dataItem
  };

  Cookies.set('itemInEditingED', dataItem["data_hash"]);
  showLoading();
  $.ajax({
    method: "POST",
    url: "/exec/montadoritem/finalizaitem/",
    data: data,
    dataType: "json"
  }).done(function (msg) {
    Cookies.remove("itemInEditingED");
    sessionStorage.removeItem('itemEditingED');
    finalizaItemAndamento = false;
    if (msg.res === true) {
      Cookies.remove('upsellItemsMontadorED');
      if((fbp_configurado == true || tiktokpixel_configurado == true) && detalhes != undefined && detalhes != null){
        if(detalhes.sabores != undefined || detalhes.sabores != null){
          let nome_item = "";
          var sabores = detalhes.sabores;

          sabores.forEach(function(sabor){
            if(sabor != null && sabor.item_sabornome != null){
              if(nome_item == ""){
                nome_item = sabor.item_sabornome;
              }
              else{
                nome_item =  nome_item + " / " + sabor.item_sabornome;
              }
            }
          });
          
          if (fbp_configurado == true) {
            fbq('track', 'AddToCart', {
                content_name: nome_item, 
                content_category: detalhes.item_tamanhonome,
                content_ids: [detalhes.item_cod],
                content_type: 'product',
                value: detalhes.item_preco,
                currency: 'BRL'
              },
              {
                eventID: facebookEventID
              }
            );
          }
          
          if (tiktokpixel_configurado == true) {
            ttq.track('AddToCart', {
              content_name: nome_item, 
              value: detalhes.item_preco,
              content_category: detalhes.item_tamanhonome,
              content_id: [detalhes.item_cod],
              content_type: 'product',
              currency: 'BRL'
            });
          }

          if (GA4_configurado) {
            gtag("event", "add_to_cart", {
              currency: "BRL",
              value: detalhes.item_preco,
              items: [
                {
                  item_id: detalhes.item_cod,
                  item_name: nome_item,
                  item_category: detalhes.item_tamanhonome,
                  price: detalhes.item_preco,
                  quantity: 1
                }
              ]
            });
          }

          if (dataItem.upsell && dataItem.upsell.length > 0) {
            for (let i = 0; i < dataItem.upsell.length; i++) {
              const itemUpsell = dataItem.upsell[i];
              if (fbp_configurado == true) {
                fbq('track', 'AddToCart', {
                    content_name: itemUpsell.itemName, 
                    content_category: itemUpsell.sessionName,
                    content_ids: [itemUpsell.itemId],
                    content_type: 'product',
                    value: itemUpsell.price,
                    currency: 'BRL'
                  },
                  {
                    eventID: facebookEventID
                  }
                );
              }
              
              if (tiktokpixel_configurado == true) {
                ttq.track('AddToCart', {
                  content_name: itemUpsell.itemName, 
                  value: itemUpsell.price,
                  content_category: itemUpsell.sessionName,
                  content_id: [itemUpsell.itemId],
                  content_type: 'product',
                  currency: 'BRL'
                });
              }

              if (GA4_configurado) {
                gtag("event", "add_to_cart", {
                  currency: "BRL",
                  value: itemUpsell.price,
                  items: [
                    {
                      item_id: itemUpsell.itemId,
                      item_name: itemUpsell.itemName,
                      item_category: itemUpsell.sessionName,
                      price: itemUpsell.price,
                      quantity: itemUpsell.amount
                    }
                  ]
                });
              }
            }
          }
        }
      }

      if(urlredir!=undefined && urlredir != null && urlredir != ""){
        document.location.href = urlredir;
        return;
      }

      if (typeof pgrediraposfinalizar != "undefined") {
        document.location.href = pgrediraposfinalizar;
      }

      hideLoading();
      peencheDadosRetorno(msg);

      if (typeof modalComboCurrent != "undefined" && modalComboCurrent) {
        (async () => {
          if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
            editorPizzaCurrent.updateDataItem(msg.item);
          }

          if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
            editorGenericCurrent.updateDataItem(msg.item);
          }

          await setItemReadyComboItems();
          renderListItemsCombo();
        })()
      }

      editorPizzaCurrent = null;
      editorGenericCurrent = null;
      itemEditing.edges = [];
      itemEditing.dough = [];
      itemEditing.observations = [];
      itemEditing.ingredients = [];
      
      return;
    } 

    hideLoading();
    if (msg.msgTitle) {
      Swal({
        type: 'warning',
        title: msg.msgTitle,
        html: msg.msg
      });
      return;
    }

    if(msg.delivery_fechado && msg.delivery_fechado == true){
      Swal({
        type: 'info',
        title: 'Delivery Online - FECHADO',
        html: `Você poderá navegar normalmente, mas não poderá adicionar itens ao pedido.<br>${htmlServiceHoursToday}`,
      });
      return;
    }

    if(msg.erro_tamanhosabores && msg.erro_tamanhosabores == true){
      Swal({
        type: 'warning',
        title: 'Erro ao Finalizar Item',
        html: msg.msg,
      });
      return;
    }

    if (msg?.errorEdge) {
      Swal({
        type: 'info',
        title: msg.msg,
        html: "Essa opção é obrigatória"
      });
      return;  
    }

    Swal({
      type: 'error',
      title: "Ocorreu um erro",
      html: msg.msg || msg.erro_msg
    });
  }).fail(function (jqXHR, textStatus) {
    Cookies.remove("itemInEditingED");
    finalizaItemAndamento = false;
    Swal({
      type: "error",
      title: "Erro ao Finalizar Item",
      text: "Ocorreu um erro.\n Tente novamente mais tarde.",
    });
  });
}

function getDataItemCurrent(){
  let data = null;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) data = editorPizzaCurrent["dataItemCurrent"];
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) data = editorGenericCurrent["dataItemCurrent"];
  
  return data;
}

function getListDough(){
  let list = listDough;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) list = editorPizzaCurrent.dough;
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) list = editorGenericCurrent.dough;
  return list;
}

function getListEdges(){
  let list = listEdges;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) list = editorPizzaCurrent.edges;
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) list = editorGenericCurrent.edges;
  return list;
}

function getListObservations(){
  let list = listObservations;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) list = editorPizzaCurrent.observations;
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) list = editorGenericCurrent.observations;
  return list;
}

function getListFlavors(){
  let list = listFlavors;
  if (typeof editorPizzaCurrent != "undefined" && editorPizzaCurrent) list = editorPizzaCurrent.flavors;
  if (typeof editorGenericCurrent != "undefined" && editorGenericCurrent) list = editorGenericCurrent.flavors;
  return list;
}

function editorUpdateDataItem(dataItem){
  if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
    editorPizzaCurrent.updateDataItem(dataItem);
    return;
  }

  if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
    editorGenericCurrent.updateDataItem(dataItem);
    return;
  }
}

function editorUpdate(){
  if (typeof editorPizzaCurrent != 'undefined' && editorPizzaCurrent) {
    editorPizzaCurrent.updateEditor();
    return;
  }

  if (typeof editorGenericCurrent != 'undefined' && editorGenericCurrent) {
    editorGenericCurrent.updateEditor();
    return;
  }
}

function zeroValueEdges(list) {
  return list.map(x => ({...x, borda_preco: 0}))
}

function zeroValueObservations(list) {
  return list.map(x => ({...x, observacoes_preco: 0}))
}

function zeroValueIngredients(list) {
  return list.map(x => ({...x, ingrediente_preco: 0}))
}

function getQuantityFlavorsAllowedByPromotionSettings(quantityFlavors, size, settings){
  const array = [];

  const getSizeSettings = settings.find(x => x["ID"] == size);
  if (!getSizeSettings) return array;

  return quantityFlavors.filter(x => (x["value"] || x) <= getSizeSettings["QTDMAX"]);
}

function getFlavorsAllowedByPromotionSettings(flavors, flavorsAllowed){
  const flavorsPromo = new Set(flavorsAllowed);
  return flavors.filter(x => flavorsPromo.has(parseInt(x["sabor_id"])))
}
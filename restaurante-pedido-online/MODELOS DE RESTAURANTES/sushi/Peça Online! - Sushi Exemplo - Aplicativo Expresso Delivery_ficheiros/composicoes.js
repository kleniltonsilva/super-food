let pricesCompositions = {};
let scriptCompositions = true;
let allCompositions = [];
let categoriesCompositions = [];
let compositionsItemMontador = {compositions: [], add: []};

$(document).ready(function(e){
  if (window.location.pathname.includes('/montar/') || (window.location.pathname.includes('/combo/') && window.location.pathname.includes('/item/'))) {
    (async() => {
      await updatePricesCompositionsCat();
      let totalPrice = 0;
      for (const key in pricesCompositions) {
        totalPrice += pricesCompositions[key];
      }

      let qtdItem = $('#qtddeitem').val();
      qtdItem = qtdItem ? qtdItem : 1;
  
      totalPrice = totalPrice * qtdItem;
  
      $(".preco_item_lanche").data('price', parseFloat($(".preco_item_lanche").data('price')) - totalPrice);
      $("#precodonome").data('price', parseFloat($("#precodonome").data('price')) - totalPrice);
    })()
  }

  $(document).on("click",".toggle_compositions", function(e){
    let catCompositionId = $(this).data('catcompositionid');
    $(`#dropAddCat${catCompositionId}`).slideToggle();
    if ($(this).find('i').text() == 'keyboard_arrow_up'){
      $(this).find('i').text('keyboard_arrow_down');
      if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
        setTimeout(function(){
          $(`.drop_composition[data-catcompositionid="${catCompositionId}"]`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
        }, 500)
      } else {
        const offset = $(this).offset().top - 44;
        $('html, body').animate({
          scrollTop: offset
        }, 800);
      }
    } else {
      $(this).find('i').text('keyboard_arrow_up');
    }
  });

  $(document).on('click', '.qtd_menos_composicao', async function(e){
    let compositionId = $(this).data('compositionid');
    let input = $(`.inputComposition[data-compositionid="${compositionId}"]`);
    let currentValue = parseInt(input.val());
    if (currentValue < 1) return;
    input.val(currentValue -1).change();
  });

  $(document).on('click', '.qtd_mais_composicao', async function(e){
    let compositionId = $(this).data('compositionid');
    let input = $(`.inputComposition[data-compositionid="${compositionId}"]`);
    let currentValue = parseInt(input.val());
    input.val(currentValue + 1).trigger('change');
  });

  $(document).on('click', '.qtd_menos_composicaoAdd', async function(e){
    let compositionId = $(this).data('compositionid');
    let input = $(`.inputCompositionAdd[data-compositionid="${compositionId}"]`);
    let currentValue = parseInt(input.val());
    if (currentValue < 1) return;
    input.val(currentValue -1).change();
  });

  $(document).on('click', '.qtd_mais_composicaoAdd', async function(e){
    let compositionId = $(this).data('compositionid');
    let input = $(`.inputCompositionAdd[data-compositionid="${compositionId}"]`);
    let currentValue = parseInt(input.val());

    input.val(currentValue + 1).change();
  });

  $(document).on('change', '.inputComposition', async function(e){
    
    let compositionId = $(this).data('compositionid');
    let catCompositionId = $(this).data('catcompositionid');
    let currentValue = $(this).data('current-value') ?? 0;
    
    if ($(this).attr('disabled')) {
      $(this).val(currentValue);
      return;
    }
    
    if ($(this).val() == currentValue) return;

    $(this).data('current-value', $(this).val());

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, $(this).val(), parseFloat($(this).data('price')));

    const check = await checkItemTargetCompositionAdd(compositionId, catCompositionId);
    if (!check) {
      $(this).val(currentValue).change();
      return;
    }
    
    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, $(this).val(), parseFloat($(this).data('price')));

    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  });

  $(document).on("change", ".inputCompositionAdd", async function(e){
    let compositionId = $(this).data('compositionid');
    let catCompositionId = $(this).data('catcompositionid');
    let currentValue = $(this).data('current-value') ?? 0;

    if ($(this).val() == currentValue) return;

    $(this).data('current-value', $(this).val());

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, $(this).val(), parseFloat($(this).data('price')), true);

    const check = await checkItemTargetCompositionAdd(compositionId, catCompositionId, 'Add');
    if (!check) {
      $(this).val(currentValue).change();
      return;
    }; 

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, $(this).val(), parseFloat($(this).data('price')), true);
    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  })

  $(document).on('click', '.input_checkbox_composition', async function(e){
    let compositionId = $(this).val();
    let catCompositionId = $(this).data('catcompositionid');
    const price = $(this).data('price') ? $(this).data('price') : 0;
    if ($(this).is(':checked')) {
      $(this).parent().removeClass('is-focused');
      await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, 1, parseFloat(price));
      const check = await checkItemTargetCompositionAdd(compositionId, catCompositionId);
      if (check) {
        $(`#list-compositionid-${compositionId}`).parent().addClass('is-checked');
        await updatePricesCompositionsCat();
        let totalPrice = 0;
        for (const key in pricesCompositions) {
          totalPrice += pricesCompositions[key];
        }

        let qtdItem = $('#qtddeitem').val();
        qtdItem = qtdItem ? qtdItem : 1;
    
        totalPrice = totalPrice * qtdItem;

        let currentPriceItem = parseFloat($(".preco_item_lanche").data('price'));
        $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));
    
        currentPriceItem =  parseFloat($("#precodonome").data('price'));
        $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

        currentPriceItem = parseFloat($(".precotitleitem").data('price'));
        $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

        currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
        $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);

        return;
      } 

      await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, -1, parseFloat(price));
      $(`#list-compositionid-${compositionId}`).prop('checked', false);
      $(`#list-compositionid-${compositionId}`).parent().removeClass('is-checked');
    } else {
      await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, -1, parseFloat(price));
      await updatePricesCompositionsCat();
      let totalPrice = 0;
      for (const key in pricesCompositions) {
        totalPrice += pricesCompositions[key];
      }

      let qtdItem = $('#qtddeitem').val();
      qtdItem = qtdItem ? qtdItem : 1;
  
      totalPrice = totalPrice * qtdItem;

      let currentPriceItem = parseFloat($(".preco_item_lanche").data('price'));
      $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));
  
      currentPriceItem =  parseFloat($("#precodonome").data('price'));
      $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

      currentPriceItem = parseFloat($(".precotitleitem").data('price'));
      $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

      currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
      $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
    }
  });

  $(document).on('change', '.input_radio_composition', async function(e){
    let compositionId = $(this).val();
    let catCompositionId = $(this).data('catcompositionid');
    if (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent) {
      for (let i = 0; i < compositionsItemMontador.compositions.length; i++) {
        if (compositionsItemMontador.compositions[i]['catCompositionId'] == catCompositionId) {
          compositionsItemMontador.compositions[i]['amount'] = 0;
        }
      }
    }

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, 1, parseFloat($(this).data('price')));
    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    $(this).addClass('radio_checked');
    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));
    
    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  });

  $(document).on('click', '.input_radio_composition.radio_checked', async function(e){
    $(this).prop('checked', false);
    $(this).parent().removeClass('is-checked');
    $(this).removeClass('radio_checked');

    let compositionId = $(this).val();
    let catCompositionId = $(this).data('catcompositionid');
    if (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent) {
      for (let i = 0; i < compositionsItemMontador.compositions.length; i++) {
        if (compositionsItemMontador.compositions[i]['catCompositionId'] == catCompositionId) {
          compositionsItemMontador.compositions[i]['amount'] = 0;
        }
      }
    }

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, -1, parseFloat($(this).data('price')));
    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));
    
    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  });

  $(document).on('click', '.input_radio_compositionAdd.radio_checked', async function(e){
    $(this).prop('checked', false);
    $(this).parent().removeClass('is-checked');
    $(this).removeClass('radio_checked');

    let compositionId = $(this).val();
    let catCompositionId = $(this).data('catcompositionid');
    if ( (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent)) {
      for (let i = 0; i < compositionsItemMontador.add.length; i++) {
        if (compositionsItemMontador.add[i]['catCompositionId'] == catCompositionId) {
          compositionsItemMontador.add[i]['amount'] = 0;
        }
      }
    }

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, -1, parseFloat($(this).data('price')), true);
    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  });

  $(document).on('change', '.input_radio_compositionAdd', async function(e){
    let compositionId = $(this).val();
    let catCompositionId = $(this).data('catcompositionid');
    if (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent) {
      for (let i = 0; i < compositionsItemMontador.add.length; i++) {
        if (compositionsItemMontador.add[i]['catCompositionId'] == catCompositionId) {
          compositionsItemMontador.add[i]['amount'] = 0;
        }
      }
    }

    await updateArrayCompositionsItemDesktop(compositionId, catCompositionId, 1, parseFloat($(this).data('price')), true);
    await updatePricesCompositionsCat();
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }

    let qtdItem = $('#qtddeitem').val();
    qtdItem = qtdItem ? qtdItem : 1;

    totalPrice = totalPrice * qtdItem;

    $(this).addClass('radio_checked');
    let currentPriceItem =  parseFloat($(".preco_item_lanche").data('price'));
    $(".preco_item_lanche").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem =  parseFloat($("#precodonome").data('price'));
    $("#precodonome").text("R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text("- R$ " + parseReal(currentPriceItem + totalPrice));

    currentPriceItem = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentPriceItem + totalPrice)})`);
  });

  $(document).on('focus', '.qtd_txt', function(){
    $(this).select();
  })
});

function getCompositionsItem(add = ""){
  return new Promise((resolve, reject) => {
    let compositionsItem = [];
    if (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent) {
      if (add == "Add") {
        compositionsItem = compositionsItemMontador.add;
      } else {
        compositionsItem = compositionsItemMontador.compositions;
      }
      resolve(compositionsItem);
      return;
    }

    compositionsItem = Array.from($(`.inputComposition${add}`)).map(element => {
      return {
        compositionId: $(element).data('compositionid'),
        catCompositionId: $(element).data('catcompositionid'),
        amount: $(element).val(),
        price: $(element).data('price')
      }
    });

    Array.from($(`.input_checkbox_composition${add}`)).map(element => {
      let amount = 0;
      if ($(element).is(':checked')) {
        amount = 1
      }

      compositionsItem.push({
        compositionId: $(element).val(),
        catCompositionId: $(element).data('catcompositionid'),
        amount,
        price: $(element).data('price')
      });
    });

    Array.from($(`.input_radio_composition${add}`)).map(element => {
      let amount = 0;
      if ($(element).is(':checked')) {
        amount = 1
      }

      compositionsItem.push({
        compositionId: $(element).val(),
        catCompositionId: $(element).data('catcompositionid'),
        amount,
        price: $(element).data('price')
      });
    });
    resolve(compositionsItem);
  });
}

function checkItemTargetCompositionAdd(compositionId, catCompositionId, add = ""){
  return new Promise(async (resolve, reject) => {    
    let allCompositions = [];
    let compositionItem = [];
    if (typeof deviceED != 'undefined' && deviceED == 'desktop' && (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent)) {
      if (add == "Add") {
        allCompositions = compositionsItemMontador.add.filter(e => e['catCompositionId'] == catCompositionId);
        compositionItem = compositionsItemMontador.add.filter(e => e['compositionId'] == compositionId);
      } else {
        allCompositions = compositionsItemMontador.compositions.filter(e => e['catCompositionId'] == catCompositionId);
        compositionItem = compositionsItemMontador.compositions.filter(e => e['compositionId'] == compositionId);
      }
    } else {
      compositionItem = Array.from($(`.inputComposition${add}[data-compositionid="${compositionId}"]`)).map(element => {
        let amount = $(element).val();

        return {
          compositionId: $(element).data('compositionid'),
          catCompositionId: $(element).data('catcompositionid'),
          amount: parseInt(amount)
        }
      });

      allCompositions = Array.from($(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`)).map(element => {
        let amount = $(element).val();
        return {
          compositionId: $(element).data('compositionid'),
          catCompositionId: $(element).data('catcompositionid'),
          amount: parseInt(amount)
        }
      });
  
      Array.from($(`.input_radio_composition${add}[data-catcompositionid="${catCompositionId}"]`)).forEach(element => {
        let amount = 0;
        if ($(element).is(':checked')) {
          amount = 1
        }
  
        allCompositions.push({
          compositionId: $(element).val(),
          catCompositionId: $(element).data('catcompositionid'),
          amount
        });
      });
  
      Array.from($(`.input_checkbox_composition${add}[data-catcompositionid="${catCompositionId}"]`)).forEach(element => {
        let amount = 0;
        if ($(element).is(':checked')) {
          amount = 1
        }
  
        allCompositions.push({
          compositionId: $(element).val(),
          catCompositionId: $(element).data('catcompositionid'),
          amount
        });
      });
    }

    const sizeId = typeof getDataItem != "undefined" ? getDataItem("sizeId") : item_tamanho;
    let configCat = await getConfigCatCompositionsByCatAndSize(catCompositionId, sizeId);

    for (let i = 0; i < configCat.length; i++) {
      let name = configCat[i]['NOME'];
      let maxAmount = parseInt(configCat[i]['maxAmount']);
      let maxAmountAdd = parseInt(configCat[i]['maxAmountAdd']);
      let maxAmountPerComposition = parseInt(configCat[i]['maxAmountPerComposition']);

      let sumAmountCompositions = 0;
      for (let x = 0; x < allCompositions.length; x++) {
        sumAmountCompositions = sumAmountCompositions + parseInt(allCompositions[x]['amount']);
      }

      //valida quantide máxima por composição
      let compositionsMoreAllowed = compositionItem.filter(element => parseInt(element['amount']) > maxAmountPerComposition);
      if (compositionsMoreAllowed.length > 0) {
        Swal({
            title: `Quantidade Inválida`,
            text: `Não é possível adicionar mais que ${maxAmountPerComposition} opções do mesmo(a) ${name}`,
            type: "info",
        });
        resolve(false);
        return;
      }

      //valida quantidade máxima
      if (add == 'Add') {
        if ((sumAmountCompositions) >= maxAmountAdd) {
          Array.from($(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`)).forEach(x => {
            if ($(x).val() == 0 && $(x).data('compositionid') != compositionId) {
              $(x).css('opacity', '0.6');
              $(x).attr('disabled', true);
            }
          });
        } else {
          $(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`).css('opacity', '1');
          $(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`).attr('disabled', false);
        }

        if (sumAmountCompositions > maxAmountAdd) {
          Swal({
              title: `Quantidade Inválida`,
              text: `Não é possível adicionar mais que ${maxAmountAdd} opções de ${name} adicionais`,
              type: "info",
          }); 
          resolve(false);
          return;
        }
      } else {
        if ((sumAmountCompositions) >= maxAmount) {
          Array.from($(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`)).forEach(x => {
            if ($(x).val() == 0 && $(x).data('compositionid') != compositionId) {
              $(x).css('opacity', '0.6');
              $(x).attr('disabled', true);
            }
          });
        } else {
          $(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`).css('opacity', '1');
          $(`.inputComposition${add}[data-catcompositionid="${catCompositionId}"]`).attr('disabled', false);
        }

        if (sumAmountCompositions > maxAmount) {
          Swal({
              title: `Quantidade Inválida`,
              text: `Não é possível adicionar mais que ${maxAmount} opções de ${name}`,
              type: "info",
          }); 
          resolve(false);
          return;
        }
      }
    }

    resolve(true);
    return;
  });
}

function checkItemCompositions(add = ""){
  return new Promise(async (resolve, reject) => {
    let compositionsItem = await getCompositionsItem(add);
    if (compositionsItem.length < 1 && add == 'Add') {
      resolve(true);
      return;
    }

    const sizeId = typeof getDataItem != "undefined" ? getDataItem("sizeId") : item_tamanho;

    let configCat = await getConfigCatCompositionsBySize(sizeId);
    for (let i = 0; i < configCat.length; i++) {
      if (!configCat[i]) {
        resolve(true);
        return;
      }
      let catId = configCat[i]['ID'];
      if (typeof configComposicoesItemCombo != 'undefined' && configComposicoesItemCombo.hasOwnProperty(catId) && add == 'Add') {
        if (configComposicoesItemCombo[catId]['COBRAR'] == 'NP') {
          continue;
        }
      }

      let name = configCat[i]['NOME'];
      let maxAmount = parseInt(configCat[i]['maxAmount']);
      let maxAmountAdd = parseInt(configCat[i]['maxAmountAdd']);
      let minAmount = parseInt(configCat[i]['minAmount']) <= maxAmount ? parseInt(configCat[i]['minAmount']) : maxAmount;
      let maxAmountPerComposition = parseInt(configCat[i]['maxAmountPerComposition']);
      let compositonsByCat = compositionsItem.filter(element => parseInt(element['catCompositionId']) == parseInt(catId) && parseInt(element['amount']) > 0);

      //valida composições obrigatórias
      if (add != 'Add') { 
        if (compositonsByCat.length < 1 && configCat[i]['availability'] == 'OBRIGATORIO') {
          Swal({
              title: `Selecione um(a) ${name}`,
              text: "Essa opção é obrigatória",
              type: "info",
              onClose: () => {
                if ($(`#linkCatComposition${catId}`).length > 0) {
                  if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
                    setTimeout(function(){
                      $(`#linkCatComposition${catId}`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
                    }, 500)
                  } else {
                    const element = document.getElementById(`linkCatComposition${catId}`);
                    if (element) {
                      element.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                      });
                    }
                  }
                }
              }
          }); 
          resolve(false);
          return;
        }
      }

      let sumAmountCompositions = 0;
      for (let x = 0; x < compositonsByCat.length; x++) {
        sumAmountCompositions = sumAmountCompositions + parseInt(compositonsByCat[x]['amount']);
      }

      //valida quantidade minima
      if (add != 'Add') {
        if (sumAmountCompositions < minAmount && configCat[i]['availability'] == 'OBRIGATORIO') {
          Swal({
              title: `Selecione mais ${name}`,
              text: `Deve selecionar no mínimo ${minAmount}`,
              type: "info",
              onClose: () => {
                if ($(`#linkCatComposition${catId}`).length > 0) {
                  if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
                    setTimeout(function(){
                      $(`#linkCatComposition${catId}`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
                    }, 500)
                  } else {
                    const element = document.getElementById(`linkCatComposition${catId}`);
                    if (element) {
                      element.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                      });
                    }
                  }
                }
              }
          }); 
          resolve(false);
          return;
        }
      }

      //valida quantidade máxima
      if (add == 'Add') {
        if (sumAmountCompositions > maxAmountAdd) {
          Swal({
              title: `Remova um(a) ou mais ${name}`,
              text: `Deve selecionar no máximo ${maxAmountAdd} adicionais`,
              type: "info",
              onClose: () => {
                if ($(`#linkCatComposition${catId}`).length > 0) {
                  if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
                    setTimeout(function(){
                      $(`#linkCatComposition${120}`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
                    }, 500)
                  } else {
                    $("html, body").animate({ scrollTop: $(`#linkCatComposition${catId}`).offset().top - 55 }, 500);
                  }
                }
              }
          }); 
          resolve(false);
          return;
        }
      } else {
        if (sumAmountCompositions > maxAmount) {
          Swal({
              title: `Remova um(a) ou mais ${name}`,
              text: `Deve selecionar no máximo ${maxAmount}`,
              type: "info",
              onClose: () => {
                if ($(`#linkCatComposition${catId}`).length > 0) {
                  if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
                    setTimeout(function(){
                      $(`#linkCatComposition${120}`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
                    }, 500)
                  } else {
                    $("html, body").animate({ scrollTop: $(`#linkCatComposition${catId}`).offset().top - 55 }, 500);
                  }
                }
              }
          }); 
          resolve(false);
          return;
        }
      }

      //valida quantide máxima por composição
      let compositionsMoreAllowed = compositonsByCat.filter(element => parseInt(element['amount']) > maxAmountPerComposition);
      if (compositionsMoreAllowed.length > 0) {
        let textAdd = add == 'Add' ? 'adicional' : '';
        Swal({
            title: `Remova um(a) ou mais ${name}`,
            text: `É permitido no máximo ${maxAmountPerComposition} opções do(a) mesmo(a) ${name} ${textAdd}`,
            type: "info",
            onClose: () => {
              if ($(`#linkCatComposition${catId}`).length > 0) {
                if ($('.contentModalItem').length > 0 || $('.contentModalCombo').length > 0) {
                  setTimeout(function(){
                    $(`#linkCatComposition${120}`)[0].scrollIntoView({behavior: 'smooth', block: 'start'})
                  }, 500)
                } else {
                  $("html, body").animate({ scrollTop: $(`#linkCatComposition${catId}`).offset().top - 55 }, 500);
                }
              }
            }
        }); 
        resolve(false);
        return;
      }
    }
    resolve(true);
  });
}

async function getConfigCatCompositionsBySize(sizeId){
  let array = [];
  if (!categoriesCompositions) return array;

  for (let i = 0; i < categoriesCompositions.length; i++) {
    const categorie = categoriesCompositions[i];
    if (categorie['CONFIG_TAMANHO'][sizeId]) {
      const checkAvailability = await checkCategorieCompositionAvailableByMontador(categorie['COD_SESSAO']);
      if (!checkAvailability) continue;
      let obj = {
        ...categorie,
        ...categorie['CONFIG_TAMANHO'][sizeId]
      }
      delete obj.CONFIG_TAMANHO;
      array.push(obj);
    }
  }
  return array;
}

function getConfigCatCompositionsByCatAndSize(catCompositionId, sizeId){
  return new Promise(async (resolve, reject) => {
    let array = [];
    for (let i = 0; i < categoriesCompositions.length; i++) {
      let element = categoriesCompositions[i];
      if (parseInt(element['ID']) == parseInt(catCompositionId) && element['CONFIG_TAMANHO'][sizeId]) {
        const checkAvailability = await checkCategorieCompositionAvailableByMontador(element['COD_SESSAO']);
        if (!checkAvailability) continue;
        let obj = {
          ...element,
          ...element['CONFIG_TAMANHO'][sizeId]
        }
        delete obj.CONFIG_TAMANHO;
        array.push(obj);
      }
    }
  
    resolve(array);
  });
}

function getTotalPriceCatComposition(catCompositionId, add = ""){
  return new Promise(async (resolve, reject) => {
    let compositions = await getCompositionsItem(add);   
    compositions = compositions.filter(element => element['catCompositionId'] == catCompositionId && parseInt(element["amount"]) > 0);
    if (compositions.length < 1) {
      resolve(0);
      return;
    }

    let bigPrice = 0;
    let avgPrice = 0;
    let totalPrice = 0;
    let compositionIdBigTotalPrice = 0;
    for (let i = 0; i < compositions.length; i++) {
      let composition = compositions[i];
      const quantity = composition["amount"];
      let price = parseFloat(composition['price']);
      bigPrice = price > bigPrice ? price : bigPrice;
      avgPrice += price * quantity;
      let totalPriceComposition = price * quantity;
      if (totalPriceComposition > totalPrice) {
        totalPrice = totalPriceComposition;
        compositionIdBigTotalPrice = composition['compositionId'];
      }
      totalPrice = (price * quantity) > totalPrice ? (price * quantity) : totalPrice;
    }
    
    avgPrice = avgPrice / compositions.length;

    let total = 0;
    let calculationCat;
    if (add == 'Add') {
      calculationCat = categoriesCompositions.filter(element => element['ID'] == catCompositionId)[0]['CALCULO_ADICIONAIS'];
    } else {
      calculationCat = categoriesCompositions.filter(element => element['ID'] == catCompositionId)[0]['CALCULO_ITENS'];
    }

    if (calculationCat == "MEDIA") {
      total = avgPrice;
      resolve(total);
      return;
    }

    if (calculationCat == "NAO_COBRAR") {
      resolve(0);
      return;
    }

    for (let i = 0; i < compositions.length; i++) {
      let composition = compositions[i];
      let amount = parseInt(composition['amount']);
      let price = 0;
      switch (calculationCat) {
        case 'MAIOR':
          if (composition['compositionId'] == compositionIdBigTotalPrice) {
            price = composition['price'];
            total += price * amount;
          }
          break;
        case 'SOMA':
          price = composition['price'];
          total += price * amount;
          break;
      }
    }
    
    resolve(total);
  });
}

function updatePricesCompositionsCat(){
  return new Promise(async (resolve, reject) => {
    for (let i = 0; i < categoriesCompositions.length; i++) {
      let catId = categoriesCompositions[i]['ID'];
      let price = await getTotalPriceCatComposition(catId,"");
      let priceAdd = await getTotalPriceCatComposition(catId, 'Add');
      pricesCompositions[catId] = price;
      pricesCompositions[`${catId}-add`] = priceAdd;

      $(`#totalPriceCat${catId}`).html(`R$ ${parseReal(price + priceAdd)}`);
    }
    resolve();
  });
}

async function getCatCompositionsBySessionAndSize(sessionId, sizeId){
  if (!categoriesCompositions || categoriesCompositions.length < 1) return false;
  const checkAvailability = await checkCategorieCompositionAvailableByMontador(sessionId);
  if (!checkAvailability) return false;
  let array = [];
  for (let i = 0; i < categoriesCompositions.length; i++) {
    if (categoriesCompositions[i]['COD_SESSAO'] == sessionId && sizeId in categoriesCompositions[i]['CONFIG_TAMANHO']) {
      if (categoriesCompositions[i]['CONFIG_TAMANHO'][sizeId]['availability'] != "INDISPONIVEL") {
        let category = {
          ...categoriesCompositions[i],
          ...categoriesCompositions[i]['CONFIG_TAMANHO'][sizeId]
        }
  
        delete category['CONFIG_TAMANHO'];
        array.push(category);
      }
    }
  }

  return array.length > 0 ? array : false;
}

function getConfigCatCompositionByIdAndSize(catCompositionId, sizeId){
  if (!categoriesCompositions || categoriesCompositions.length < 1) return false;
  
  let config = categoriesCompositions.filter(e => e['ID'] == catCompositionId);
  if (config.length > 0) {
    if (sizeId in config[0]['CONFIG_TAMANHO']) {
      let obj = {
        ...config[0],
        ...config[0]['CONFIG_TAMANHO'][sizeId]
      }
      
      delete obj['CONFIG_TAMANHO'];
      return obj;
    }
  }
  return false;
}

function getCompositionsByCategorieAndSize(catCompositionId, sizeId){
  if (!allCompositions || allCompositions.length < 1) return false;
  
  let array = [];
  for (let i = 0; i < allCompositions.length; i++) {
    if (allCompositions[i]['COD_CAT_COMPOSICAO'] == catCompositionId) {
      let configSize = allCompositions[i]['CONFIG_TAMANHO'].filter(e => e['COD_TAMANHO'] == sizeId);

      if (configSize.length) {
        if (configSize[0]['STATUS'] == 'A') {
          let composition = {
            ...allCompositions[i],
            ...configSize[0]
          }
    
          delete composition['CONFIG_TAMANHO'];
          array.push(composition);
        }
      }
    }
  }

  return array.length > 0 ? array : false;
}

function updateArrayCompositionsItemDesktop(compositionId, catCompositionId, amount, price, add = false){
  return new Promise((resolve, reject) => {
    if (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent) {
      let hasComposition = false;
      let objComposition = {
        compositionId,
        catCompositionId,
        amount,
        price,
      }

      let type = 'compositions';
      if (add) type = 'add';
      for (let i = 0; i < compositionsItemMontador[type].length; i ++) {
        if (compositionsItemMontador[type][i]['compositionId'] == compositionId) {
          compositionsItemMontador[type][i] = objComposition;
          hasComposition = true;
          break;
        }
      }
  
      if (!hasComposition) {
        compositionsItemMontador[type].push(objComposition);
      }

      if (typeof itemEditing != 'undefined') {
        itemEditing["compositions"] = compositionsItemMontador["compositions"]
        itemEditing["compositionsAdd"] = compositionsItemMontador["add"]
        sessionStorage.setItem("itemEditingED", JSON.stringify(itemEditing))
      }
    }
    resolve(true);
  });
}

function resetArrayCompositionsItem(){
  compositionsItemMontador.compositions = [];
  compositionsItemMontador.add = [];
  pricesCompositions = {};
  $('.inputCompositionAdd').val(0);
  $('.inputComposition').val(0);
}

async function updateValuesCompositionsTotalOrderDesktop(){
  if (typeof deviceED != 'undefined' && deviceED == 'desktop' && (window.location.pathname.includes('/cardapio') && (typeof editorGenericCurrent == "undefined" || !editorGenericCurrent))) {
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }
    
    let currentTotal = parseFloat($(".precotitleitem").data('price'));
    $(".precotitleitem").text(" - R$ " + parseReal(currentTotal + totalPrice));
  }
}

async function updateValuesCompositionsTotalOrderGerenciador(){
  if (typeof deviceED != 'undefined' && deviceED == 'desktop' && (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent)) {
    let totalPrice = 0;
    for (const key in pricesCompositions) {
      totalPrice += pricesCompositions[key];
    }
    
    let currentTotal = parseFloat($("#btnfinalizamont").data('price'));
    $("#btnfinalizamont").html(`<i class='sprite sprite-ok_branco'></i> FINALIZAR ITEM (R$ ${parseReal(currentTotal + totalPrice)})`);
  }
}

async function getTotalPriceAllCompositionsItem(compositions, compositionsAdd){
  let totalPrice = 0;

  if (compositions) {
    for (const composition of compositions) {
      totalPrice += parseFloat(composition['price']) * parseInt(composition['amount']);
    }
  }

  if (compositionsAdd) {
    for (const composition of compositionsAdd) {
      totalPrice += parseFloat(composition['price']) * parseInt(composition['amount']);
    }
  }

  return totalPrice;
}

function checkCategorieCompositionAvailableByMontador(sessionId) {
  return new Promise((resolve, reject) => {
    if (typeof deviceED != 'undefined' && deviceED == 'desktop' && (typeof editorPizzaCurrent == "undefined" || !editorPizzaCurrent)) {
      let sessionNotAllowed = sessoes_itens.filter( e => e['sessao_id'] == sessionId && e['sessao_paginamontador'] && e['sessao_paginamontador'] != "montador-slider");
      if (sessionNotAllowed.length > 0) {
        resolve(false);
        return;
      }
      resolve(true);
      return;
    }

    let session = sessionId ? listSessions.find(x => x["sessao_id"] == sessionId) : sessao_item;
    session = session ?? sessao_item;

    if (session['sessao_paginamontador'] && session['sessao_paginamontador'].length > 2) {
      resolve(false);
      return;
    }

    resolve(true);
    return;
  });
}

function renderListCompositions(){
  let htmlCompositions = "";
  if (!categoriesCompositions || !allCompositions) {
    return htmlCompositions;
  }

  const sizeId = getDataItem("sizeId");

  for (const catComposition of categoriesCompositions) {
    let compositionsByCat = getCompositionsByCategorieAndSize(catComposition["ID"], sizeId);
    if (!compositionsByCat) {
      continue;
    }

    const sortingType = catComposition["TIPO_ORDENACAO_COMPOSICOES"];
    compositionsByCat = ordenaListaComposicoes(sortingType, compositionsByCat);

    const catConfigSize = catComposition["CONFIG_TAMANHO"][sizeId] ?? false;
    if (!catConfigSize || catConfigSize['availability'] == 'INDISPONIVEL') {
      continue;
    }

    let calculationAddCombo = false;
    if (typeof configComposicoesItemCombo != "undefined" && Object.keys(configComposicoesItemCombo).length > 0) {
      calculationAddCombo = configComposicoesItemCombo[catComposition["ID"]] ?? {COBRAR: 'S'};
    }

    if (typeof itemSettings != "undefined" && itemSettings) {
      calculationAddCombo = itemSettings["OPCIONAIS"]["COMPOSICOES"][catComposition["ID"]] ?? {COBRAR: 'S'};
    }

    let htmlAdd = "";
    const catAvailability = catConfigSize["availability"];
    const catCalculation = catComposition["CALCULO_ITENS"];
    const catMaxAmount = parseInt(catConfigSize["maxAmount"]);
    const catMinAmount = parseInt(catConfigSize["minAmount"]);
    const catMaxAmountAdd = parseInt(catConfigSize["maxAmountAdd"]);
    const catMaxAmountPerComposition = parseInt(catConfigSize["maxAmountPerComposition"]);

    const textAvailability = catAvailability == "OBRIGATORIO" ? "Obrigatório" : "Opcional";
    const textOptions = catMaxAmount > 1 ? "opções" : "opção";
    let textAmount = `Selecione até ${catMaxAmount} ${textOptions} (${textAvailability})`;
    textAmount = catAvailability == "OBRIGATORIO" ? `Selecione ${catMaxAmount} ${textOptions} (${textAvailability})` : textAmount;
    if (catAvailability == "OBRIGATORIO" && catMaxAmount > catMinAmount && catMaxAmount > 1) {
      $textAmount = `Selecione de ${catMinAmount} à ${catMaxAmount} opções (${textAvailability})`;
    }

    htmlCompositions += `
      <ul class='list_ing mdl-list' id="linkCatComposition${catComposition["ID"]}">
        <li class='tit_ing drop_composition'>
          <div class="div_title_drop_composition">
            <i class='material-icons'>keyboard_arrow_down</i> 
            ${catComposition["NOME"]}
          </div>
          <div class="div_info_drop_composition">
            <span>${textAmount}</span>
    `;

    if (catCalculation !== 'NAO_COBRAR') {
      htmlCompositions += `
        <span>Total: <span id="totalPriceCat${catComposition["ID"]}">R$ 0,00</span></span>
      `;
    }

    htmlCompositions += `
        </div>
      </li>
    `;

    let hasAdd = false;
    for (const composition of compositionsByCat) {
      let nameComposition = composition["NOME"];
      nameComposition += (composition["PRECO"] > 0) && catCalculation != "NAO_COBRAR" ? ` + R$ ${parseReal(composition["PRECO"])}` : "";
      const price = catCalculation != "NAO_COBRAR" ? composition["PRECO"] : 0;
      const compositionId = composition["ID"];
      let compositionChecked = "";
      let compositionAmount = 0;
      let compositionCheckedAdd = "";
      let compositionAmountAdd = 0;

      htmlCompositions += `
        <li>
          <label class='mdl-list__item itemComposition' for='list-compositionid-${compositionId}'>
            <span class='mdl-list__item-primary-content'>
              ${nameComposition}
            </span>
      `;

      if (catMaxAmount == 1) {
        htmlCompositions += `
          <label class='mdl-radio mdl-js-radio radio_composition' for='list-compositionid-${compositionId}'>
            <input type='radio' id='list-compositionid-${compositionId}' name='catcomposition${catComposition["ID"]}' class='mdl-radio__button input_radio_composition' value='${compositionId}' data-price='${price}' data-catcompositionid='${catComposition['ID']}' ${compositionChecked}>
            <span class='mdl-radio__label'></span>
          </label>
        `;
      } else if (catMaxAmountPerComposition == 1) {
        htmlCompositions += `
          <div>
            <label class='mdl-checkbox mdl-js-checkbox label_checkbox_composition' for='list-compositionid-${compositionId}'>
              <input type='checkbox' readonly='false' id='list-compositionid-${compositionId}' class='mdl-checkbox mdl-checkbox__input input_checkbox_composition' value='${compositionId}' data-price='${price}' data-catcompositionid='${catComposition["ID"]}' ${compositionChecked}>
            </label>
          </div>
        `;
      } else {
        htmlCompositions += `
          <div class='btn_qtd_card'>
            <span class='qtd_menos qtd_menos_composicao' data-catcompositionid='${catComposition["ID"]}' data-compositionId='${compositionId}' data-target-combo=''>-</span>
            <input class='qtd_txt inputComposition inteiro' data-catcompositionid='${catComposition["ID"]}' data-price='${price}' data-compositionid='${compositionId}' value="${compositionAmount}" data-current-value='${compositionAmount}'>
            <span class='qtd_mais qtd_mais_composicao' data-catcompositionid='${catComposition["ID"]}' data-compositionId='${compositionId}' data-catcompositionid='${catComposition["ID"]}' data-target-combo=''>+</span>
          </div>
        `;
      }
      htmlCompositions += `
          </label>
        </li>
      `;

      // configura os adicionais
      if (catCalculation == 'NAO_COBRAR' && composition["ADICIONAL"] == "A" && catMaxAmountAdd > 0) {
        nameCompositionAdd = composition["NOME"];
        if (calculationAddCombo["COBRAR"] == "N") {
          composition["PRECO"] = 0;
        }

        nameCompositionAdd += (composition["PRECO"] > 0) ? ` + R$ ${parseReal(composition["PRECO"])}` : "";
        htmlAdd += `
          <li>
            <label class='mdl-list__item itemComposition' for='add-list-compositionid-${compositionId}'>
              <span class='mdl-list__item-primary-content'>
                ${nameCompositionAdd}
              </span>
        `;

        if (catMaxAmountAdd == 1) {
          htmlAdd += `
            <label class='mdl-radio mdl-js-radio radio_composition' for='add-list-compositionid-${compositionId}'>
              <input type='radio' id='add-list-compositionid-${compositionId}' name='addCatcomposition${catComposition["ID"]}' class='mdl-radio__button input_radio_compositionAdd' value='${compositionId}' data-price='${composition["PRECO"]}' data-catcompositionid='${catComposition["ID"]}' ${compositionCheckedAdd}>
              <span class='mdl-radio__label'></span>
            </label>
          `;
        } else {
          htmlAdd += `
            <div class='btn_qtd_card'>
              <span class='qtd_menos qtd_menos_composicaoAdd' data-catcompositionid='${catComposition["ID"]}' data-compositionId='${compositionId}' data-target-combo=''>-</span>
              <input class='qtd_txt inputCompositionAdd inteiro' data-catcompositionid='${catComposition["ID"]}' data-price='${composition["PRECO"]}' data-compositionid='${compositionId}' value="${compositionAmountAdd}" data-current-value='${compositionAmountAdd}'>
              <span class='qtd_mais qtd_mais_composicaoAdd' data-compositionId='${compositionId}' data-catcompositionid='${catComposition["ID"]}' data-target-combo=''>+</span>
            </div>
          `;
        }
        htmlAdd += `
            </label>
          </li>
        `;
      }
    }
    htmlCompositions += `
        </ul>
    `;

    if (htmlAdd) {
      if (calculationAddCombo["COBRAR"] == "NP") {
        continue;
      }
      const displayTotalAdd = calculationAddCombo["COBRAR"] == 'N' ? 'style=display:none;' : '';
      const textOptionsAdd = catMaxAmountAdd > 1 ? 'opções adicionais' : 'opção adicional';
      
      htmlAdd = `
        <ul class='list_ing mdl-list'>
          <li class='tit_ing drop_composition toggle_compositions' data-catcompositionid="${catComposition["ID"]}">
            <div class="div_title_drop_composition">
              <i class='material-icons'>keyboard_arrow_up</i> 
              ${catComposition["NOME"]} - Adicional
            </div>
            <div class="div_info_drop_composition">
              <span>Selecione até ${catMaxAmountAdd} ${textOptionsAdd}</span>
              <span ${displayTotalAdd} >Total: <span id="totalPriceCat${catComposition["ID"]}">R$ 0,00</span></span>
            </div>
          </li>
          <div id='dropAddCat${catComposition["ID"]}' style="display:none;">${htmlAdd}</div>
        </ul>
      `;

      htmlCompositions += htmlAdd;
    }
  }

  return htmlCompositions;
}
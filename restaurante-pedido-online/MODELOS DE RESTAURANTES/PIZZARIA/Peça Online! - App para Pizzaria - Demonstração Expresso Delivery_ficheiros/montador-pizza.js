let showTotalPrice = true;

$(document).ready(function(e){  
  if (isMobile) {
    if (!massas_lista || massas_lista.length == 0) {
      $('#areamassa').hide();
    }
  }

  $(document).on('click', '#pizzaNumberFlavorsAdd', function(e){
    if ($(this).parent().parent().hasClass("component_editor_pizza_buttons_actions")) {
      e.preventDefault();
      return;
    }
    
    updatePizzaNumberFlavors('add');
  });

  $(document).on('click', '#pizzaNumberFlavorsRemove', function(e){
    if ($(this).parent().parent().hasClass("component_editor_pizza_buttons_actions")) {
      e.preventDefault();
      return;
    }

    updatePizzaNumberFlavors('remove');
  });
})

function startEditorMobile(options = null){
  editorPizzaCurrent = new EditorPizza(typeEditor, dadositem, dadositem['item_hash'], nomeborda, '#cont_mont_lanche', allowedExtraInfo, htmlUpsell, options, showTotalPrice);
  editorPizzaCurrent.build();
}

function updatePizzaNumberFlavors(action) {
  const itemData = $("#cont_mont_lanche").data("dadositem");
  const sizeId = itemData.item_tamanhoid;
  const numberFlavors = get_qtdSabores_tm(sizeId).map(x => parseInt(x));
  let numberFlavorsItem = parseInt(itemData.item_qtdsabor);

  const findIndex = numberFlavors.findIndex(x => x == numberFlavorsItem);

  if (action === 'add') {
    const newIndex = findIndex + 1;
    if (numberFlavors[newIndex] === undefined) return;

    numberFlavorsItem = numberFlavors[newIndex];
  }

  if (action === 'remove') {
    if (findIndex === 0) return;

    const newIndex = findIndex - 1;
    numberFlavorsItem = numberFlavors[newIndex];
  }
  
  const data = {
    qtdsabor: numberFlavorsItem
  };

  const updateAction = "alterar";
  const itemDataCurrent = $("#cont_mont_lanche").data("dadosdoitematual");
  updateNumberFlavors(itemDataCurrent, data, updateAction);
}

function setPriceEditorPizzaDesktop(data){
  let total = data.item_preco;

  if (itemSettings) {
    if (itemSettings["OPCIONAIS"]["BORDAS"]["COBRAR"] == "N" && data.item_borda) {
      const edgePrice = data.item_borda.reduce((acc, cur) => acc + cur.item_bordapreco, 0)
      total = total - edgePrice;
    }

    if (itemSettings["OPCIONAIS"]["OBSERVASOES"]["COBRAR"] == "N" && data.item_observacoes) {
      const observationsPrice = data.item_observacoes.reduce((acc, cur) => acc + cur.item_observacaopreco, 0)
      total = total - observationsPrice;
    }

    if (itemSettings["OPCIONAIS"]["INGREDIENTE"]["COBRAR"] == "N" && !data?.ingredientsPriceUpdated) {
      let ingredientsTotal = 0;

      for (const flavor of data.sabores) {
        if (flavor.item_saboringredcom) {
          const ingredientsPrice = flavor.item_saboringredcom.reduce((acc, cur) => acc + parseFloat(cur.ingrediente_preco) * cur.ingrediente_qtd, 0)
          ingredientsTotal += ingredientsPrice;
        }
      }

      total = total - ingredientsTotal;
    }
  }

  $("#preco-pizzabtn p").html(`<span>R$</span>${parseReal(total)}`);
}

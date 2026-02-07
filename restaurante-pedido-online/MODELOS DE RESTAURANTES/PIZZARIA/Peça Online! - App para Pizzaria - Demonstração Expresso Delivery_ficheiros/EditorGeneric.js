let editorGenericCurrent = null;

class EditorGeneric extends Editor{
  constructor(dataItem, hashItem, edgeName, targetRender, allowedExtraInfo = false, htmlUpsell = "", allowedOptions = null) {
    super();
    this.dataItem = dataItem;
    this.dataItemCurrent = {
      data_hash: hashItem,
      data_qtdsabor: dataItem['item_qtdsabor'],
      data_tamanho: dataItem['item_tamanhoid'],
      data_sabor: dataItem['sabores'].map(x => parseInt(x["item_saborid"])),
      data_obs: dataItem['item_obs'],
      data_bordas: dataItem['item_borda']
    };
    this.edgeName = edgeName;
    this.allowedExtraInfo = allowedExtraInfo;
    this.htmlUpsell = htmlUpsell;
    this.marginExtraInfo = this.htmlUpsell.length > 0 ? "style='margin-bottom:0px!important;'" : "";
    this.targetRender = targetRender;
    this.baseClass = 'component_editor_generic';
    this.allowedOptions = allowedOptions;
    this.showEdges = (!listEdges || listEdges.length == 0) || (this.dataItem.item_borda != undefined && this.dataItem.item_borda != false && this.dataItem.item_borda.length > 0) ? "" : " style='display: none;' " ;
    this.showObservations = (!listObservations || listObservations.length == 0) || (this.dataItem.item_observacoes != undefined && this.dataItem.item_observacoes != false && this.dataItem.item_observacoes.length > 0) ? "" : " style='display: none;' " ;
    this.instanceHash = (Math.random() + 1).toString(36).substring(4);
  }

  updateDataItem(data){
    this.dataItem = {
      ...this.dataItem,
      ...data
    };
    this.dataItemCurrent["data_qtdsabor"] = data["item_qtdsabor"];
    this.dataItemCurrent["data_tamanho"] = data["item_tamanhoid"];
    this.dataItemCurrent["data_sabor"] = data['sabores'].map(x => parseInt(x["item_saborid"])),
    this.dataItemCurrent["data_obs"] = data["item_obs"];
    this.dataItemCurrent["data_bordas"] = data["item_borda"];

    this.setListSizes();
    this.setListFlavors();
    this.setListDough();
    this.setListEdges();
    this.setListObservations();
  }

  build(){
    if (typeof editorPizzaCurrent != "undefined") editorPizzaCurrent = null;
    if (typeof compositionsItemMontador != "undefined") {
      compositionsItemMontador["compositions"] = [];
      compositionsItemMontador["add"] = [];
    }
    if (typeof configComposicoesItemCombo != "undefined") {
      configComposicoesItemCombo = this.allowedOptions["options"]["COMPOSICOES"] ?? {};
    }

    this.setListSizes();
    this.setListFlavors();
    this.setListDough();
    this.setListEdges();
    this.setListObservations();
    this.setDough();
    this.setEdges();
    this.setObservations();
    this.setIngredients();
    $(this.targetRender).html(this.getRender());
    setConfigItem();
    this.renderFlavors();
    this.renderItemEdge();
    this.renderItemDough();
    this.renderItemObservations();
    this.renderItemCompositions();
    this.renderItemExtraInfo();


    if (this.sizes.length == 1) {
      $(`.${this.baseClass}_div_select_sizes`).hide();
    } else {
      $(`.updateSize`).select2({
        language: "pt-BR",
        minimumResultsForSearch: Infinity
      });
    }

    $(`.${this.baseClass}_quantity_flavors`).select2({
      language: "pt-BR",
      minimumResultsForSearch: Infinity
    });
    
    const thisClass = this;
    $(document).on('change', `.${thisClass.instanceHash} .${thisClass.baseClass}_quantity_flavors`, function(e){
      const value = $(this).val();
      thisClass.updatePizzaNumberFlavors(value);
    });

    $(document).on("change", `.${thisClass.instanceHash} .updateSize`, function (e) {  
      const sizeId = $(this).val();
      const data = {
        tamanho: sizeId
      };

      const action = "alterar";
      updateSize(thisClass.dataItemCurrent, data, action);
    });

    $(document).on("click", `.${thisClass.instanceHash} .${thisClass.baseClass}_btn_finish`, async function(e){
      let obs = $('#obs_item').val();

      if(obs && obs.length > 0 && (obs.length < 3 || obs.length > 140)){
        Swal({
          type: "warning",
          title: "Observação Inválida",
          html: 'A observação deve ter entre 3 e 140 caracteres.'
        }); 
        return;
      }
      thisClass.dataItemCurrent.data_obs = obs;

      if (typeof scriptCompositions != 'undefined' && scriptCompositions) {
        const checkCompositions = await checkItemCompositions();
        if (!checkCompositions) {
          return;
        }
  
        const checkCompositionsAdd = await checkItemCompositions('Add');
        if (!checkCompositionsAdd) {
          return;
        }
  
        thisClass.dataItemCurrent["compositions"] = await getCompositionsItem();
        thisClass.dataItemCurrent["compositionsAdd"] = await getCompositionsItem('Add');
      }

      const upsellItemsAdd = await getUpsellItemsProduct();
      if (upsellItemsAdd) thisClass.dataItemCurrent["upsell"] = upsellItemsAdd;
      
      thisClass.dataItemCurrent["dough"] = JSON.stringify(itemEditing["dough"]);
      thisClass.dataItemCurrent["edges"] = JSON.stringify(itemEditing["edges"]);
      thisClass.dataItemCurrent["observations"] = JSON.stringify(itemEditing["observations"]);
      thisClass.dataItemCurrent["ingredients"] = JSON.stringify(itemEditing["ingredients"]);

      addCustomItem(thisClass.dataItemCurrent);
    });

    $(document).on("click", `.${thisClass.instanceHash} .${thisClass.baseClass}_edit_ingredients`, function(e){
      if (e.target.classList.contains('component_editor_generic_remove_flavor')) {
        e.preventDefault();
        return;
      }

      const flavorId = $(this).data('flavorid');
      const slice = $(this).data('slice');
      flavorEditing["id"] = flavorId;
      flavorEditing["slice"] = slice;

      const flavor = thisClass.getFlavorById(flavorId);
      const flavorName = flavor["sabor_nome"];
      
      const dataIngredients = thisClass.getIngredients(flavorId);
      openModalIngredients(dataIngredients, flavorName);
    });

    $(document).on("blur", `.${thisClass.instanceHash} #obs_item`, function (e) {
        thisClass.extraInfoCurrent = $(`.${thisClass.instanceHash} #obs_item`).val();
      }
    );
  }

  getRender(){
    return `
      <div style="background: none!important;" id="${this.baseClass}_container" class="${this.instanceHash} ${this.baseClass}_type_editor" data-dadositem='${JSON.stringify(this.dataItem)}' data-dadosdoitematual='${JSON.stringify(this.dataItemCurrent)}'>
        <div class="${this.baseClass}_price_img">
          <h2 class="${this.baseClass}_session_name">${this.dataItem["item_sessaonome"]} <span class="${this.baseClass}_price total_price_item">R$ 0,00</span></h2>
          <img src="" alt="${this.dataItem["item_sessaonome"]}" class="${this.baseClass}_img"/>
        </div>
        <div class="${this.baseClass}_settings">
          <div class="${this.baseClass}_div_select_sizes">
            <label class="${this.baseClass}_label_sizes">Tamanho:</label>
            <select class="${this.baseClass}_drop_size updateSize" name="tamanho" data-nomecampo="Tamanho" autocomplete="off" data-tipocampo="select" required="true">
              ${this.renderSizes()}
            </select>
          </div>
          <div class="${this.baseClass}_div_select_quantity_flavors">
            <label class="${this.baseClass}_label_quantity_flavors">Sabores:</label>
            <select class="${this.baseClass}_quantity_flavors" name="qtdsabores" data-nomecampo="qtdsabores" autocomplete="off" data-tipocampo="select" required="true">
              ${this.renderNumberFlavors()}
            </select>
          </div>
        </div>        
        <div class="${this.baseClass}_options">
          <div class="${this.baseClass}_div_flavors">
          </div>
          <span class='${this.baseClass}_dough openModalDough'>Selecione uma Massa</span>
          <span class='${this.baseClass}_edges openModalEdges'>Selecionar Borda</span>
          <span class='${this.baseClass}_observations openModalObservations'>Observações</span>
          <div class='${this.baseClass}_compositions'></div>
          ${!this.allowedExtraInfo ? "" : `<textarea rows='3' maxlength=140 minlength=3 id='obs_item' placeholder='Alguma observação?' class='inputCampo2' ${this.marginExtraInfo}></textarea>`}
        </div>
      </div>
      <div class="${this.baseClass}_div_btn_finish ${this.instanceHash}">
        <div class="${this.baseClass}_btn_finish">
          <p><i class="material-icons">shopping_cart</i> Pronto! Voltar ao Combo</p>
        </div>
      </div>
      <div class="${this.baseClass}_backdrop backdrop"></div>
      <div class="modal fade ${this.baseClass}_modalEddy modalEddy" tabindex="-1" aria-labelledby="itemModal" aria-hidden="true"></div>
    `;
  }

  updateEditor(){
    $(this.targetRender).html(this.getRender());

    if (this.targetRender == ".component_modal_combo_items") {
      $(`.${this.baseClass}_price`).hide();
    }

    setConfigItem();
    this.renderItemEdge();
    this.renderItemDough();
    this.renderItemObservations();
    this.renderFlavors();
    this.updateItemCompositions();
    this.renderItemExtraInfo();

    if (this.sizes.length == 1) {
      $(`.${this.baseClass}_div_select_sizes`).hide();
    } else {
      $(".updateSize").select2({
        language: "pt-BR",
        minimumResultsForSearch: Infinity
      });
    }

    $(`.${this.baseClass}_quantity_flavors`).select2({
      language: "pt-BR",
      minimumResultsForSearch: Infinity
    });
  }

  renderFlavors(){
    const domainImages = urlsfiles["imagens"];
    const imgId = this.dataItem["sabores"][0]["item_saborfotoid"];
    const imgName = this.dataItem["sabores"][0]["item_saborfotonome"];
    const img = `${domainImages}produtos/${imgId}/240/${imgName}`;
    const sizeId = this.dataItem.item_tamanhoid;
    const numberFlavors = this.getQuantityFlavorBySize(sizeId);
    let quantityFlavorCurrent = this.dataItem["item_qtdsabor"];
    
    quantityFlavorCurrent = numberFlavors.filter(x => parseInt(x) == parseInt(quantityFlavorCurrent) || parseInt(x) > parseInt(quantityFlavorCurrent))[0];
    if (!quantityFlavorCurrent) {
      quantityFlavorCurrent = numberFlavors.slice(-1);
    }

    $(`.${this.baseClass}_img`).attr("src", img);

    let html = "";

    for (let i = 1; i <= quantityFlavorCurrent; i++){
      const getFlavorItem = this.dataItem["sabores"].find(x => x["item_saborpedaco"] == i);
      if (getFlavorItem) {
        const flavorId = getFlavorItem["item_saborid"];
        const flavorName = getFlavorItem["item_sabornome"];
        html += `
          <span class='${this.baseClass}_flavor ${this.baseClass}_edit_ingredients' data-slice="${i}" data-flavorid="${flavorId}">${flavorName}
            <span class="material-icons ${this.baseClass}_remove_flavor openModalFlavors" data-slice="${i}">close</span>
          </span>`;
        continue;
      }

      html += `<span class='${this.baseClass}_flavor_empty openModalFlavors' data-slice="${i}">Selecione um Sabor</span>`;
    }

    $(`.${this.baseClass}_div_flavors`).html(html);

    if (numberFlavors.length == 1) {
      $(`.${this.baseClass}_div_select_quantity_flavors`).hide();
      $(`.${this.baseClass}_div_select_sizes`).css("width", "100%");
      $(`.${this.baseClass}_div_select_sizes .select2-container`).css("width", "100%");
    } else if (this.sizes.length == 1){
      $(`.${this.baseClass}_div_select_sizes`).hide();
      $(`.${this.baseClass}_div_select_quantity_flavors`).show();
      $(`.${this.baseClass}_div_select_quantity_flavors`).css("width", "100%");
      $(`.${this.baseClass}_div_select_quantity_flavors .select2-container`).css("width", "100%");
    } else {
      $(`.${this.baseClass}_div_select_quantity_flavors`).show();
      $(`.${this.baseClass}_div_select_sizes`).css("width", "57%");
    }
  }

  renderNumberFlavors(){
    const sizeId = this.dataItem.item_tamanhoid;
    const numberFlavors = this.getQuantityFlavorBySize(sizeId);
    let quantityFlavorCurrent = this.dataItem["item_qtdsabor"];

    quantityFlavorCurrent = numberFlavors.filter(x => parseInt(x) == parseInt(quantityFlavorCurrent) || parseInt(x) > parseInt(quantityFlavorCurrent))[0];
    if (!quantityFlavorCurrent) {
      quantityFlavorCurrent = numberFlavors.slice(-1);
    }

    let options = "";
  
    for (let i = 0; i < numberFlavors.length; i++) {
      const number = numberFlavors[i];
      const name = number == 1 ? `${number} sabor` : `${number} sabores`;
      const selected = number == quantityFlavorCurrent ? "selected" : "";
      options += `<option value="${number}" ${selected}>${name.toUpperCase()}</option>`;
    }

    return options;
  }

  renderItemEdge(){
    if (this.edges.length == 0) {
      $(`.${this.baseClass}_edges`).hide();
      return;
    }

    let nameEdge = "Borda";
    if (this.edges.length > 0) {
      nameEdge = this.edges[0]["name"] ? this.edges[0]["name"].split(':')[0] : this.edges[0]["borda_nome"].split(':')[0];
    }

    $(`.${this.baseClass}_edges`).html(`Selecionar ${nameEdge}`);
    $(`.${this.baseClass}_edges`).show();
  }

  renderItemDough(){
    if (this.dough.length == 0) {
      $(`.${this.baseClass}_dough`).hide();
      return;
    }
  
    let nameDough = "Massa";
    if (this.dough.length > 0) {
      nameDough = this.dough[0]["name"] ? this.dough[0]["name"].split(':')[0] : this.dough[0]["massa_nome"].split(':')[0];
    }

    const dough = itemEditing.dough;
    const getDough = this.dough.find(x => (x["id"] ?? x["massa_id"]) == dough["id"]);
    if (getDough && getDough['allowsEdge'] == "N") {
      itemEditing.edges = [];
      $(`.${this.baseClass}_edges`).hide();
    } else {
      if (itemEditing.edges.length == 0 && this.edges.length > 0) {
        $(`.${this.baseClass}_edges`).show();
      }
    }

    $(`.${this.baseClass}_dough`).html(`Selecionar ${nameDough}`);
    $(`.${this.baseClass}_dough`).show();
  }

  renderItemObservations(){
    if (this.observations.length == 0) {
      $(`.${this.baseClass}_observations`).hide();
      return;
    }

    $(`.${this.baseClass}_observations`).show();
  }

  updateItemCompositions(){
    this.renderItemCompositions("update");
  }

  async renderItemCompositions(type = "item"){
    const html = renderListCompositions();
    if (html.length == 0) {
      $(`.${this.baseClass}_compositions`).hide();
      return;
    }

    $(`.${this.baseClass}_compositions`).html(renderListCompositions());
    $(`.${this.baseClass}_compositions`).show();
    componentHandler.upgradeDom();

    const compositions = type == "update" ? compositionsItemMontador["compositions"] : this.dataItem["item_compositions"];
    const compositionsAdd = type == "update" ? compositionsItemMontador["add"] : this.dataItem["item_compositionsAdd"];

    if (type == "update") {
      compositionsItemMontador["compositions"] = [];
      compositionsItemMontador["add"] = [];
    }

    const sleep = () => new Promise(r => setTimeout(r, 100));

    if (compositions) {
      for (const composition of compositions) {
        const id = composition["compositionId"];
        const quantity = composition["amount"];

        if (quantity == 0) continue;

        if ($(`#list-compositionid-${id}`).length > 0) {
          $(`#list-compositionid-${id}`).click();
          continue;
        }

        if ($(`.inputComposition[data-compositionid="${id}"]`).length > 0) {
          for (let i = 0; i < quantity; i++) {
            $(`.qtd_mais_composicao[data-compositionid="${id}"]`).click();
            await sleep();
          }
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

        if ($(`.inputCompositionAdd[data-compositionid="${id}"]`).length > 0) {
          for (let i = 0; i < quantity; i++) {
            $(`.qtd_mais_composicaoAdd[data-compositionid="${id}"]`).click();
            await sleep();
          }
        }
      }
    }
  }

  updatePizzaNumberFlavors(value) {    
    const data = {
      qtdsabor: value
    };
  
    const updateAction = "alterar";
    updateNumberFlavors(this.dataItemCurrent, data, updateAction);
  }
}
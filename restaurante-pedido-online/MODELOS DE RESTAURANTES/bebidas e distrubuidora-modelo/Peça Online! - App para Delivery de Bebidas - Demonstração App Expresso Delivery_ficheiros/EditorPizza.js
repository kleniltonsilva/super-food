let editorPizzaCurrent = null;

class EditorPizza extends Editor{
  constructor(typeEditor, dataItem, hashItem, edgeName, targetRender, allowedExtraInfo = false, htmlUpsell = "", allowedOptions = null, showTotalPrice = false) {
    super();
    this.typeEditor = typeEditor;
    this.imgBackgroundPizza = typeEditor == 'montarpizza' ? 'forma' : 'formaquadrada';
    this.dataItem = dataItem;
    this.dataItemCurrent = {
      data_hash: hashItem,
      data_qtdsabor: dataItem['item_qtdsabor'],
      data_tamanho: dataItem['item_tamanhoid'],
      data_sabor: dataItem['sabores'].map(x => parseInt(x["item_saborid"])),
      data_obs: dataItem['item_obs'],
      data_bordas: dataItem['item_borda']
    };
    urlsfiles
    this.urlImageHand = `${urlsfiles["media"]}0.01.001/img/icon_cursor.png`;
    this.edgeName = edgeName;
    this.allowedExtraInfo = allowedExtraInfo;
    this.htmlUpsell = htmlUpsell;
    this.marginExtraInfo = this.htmlUpsell.length > 0 ? "style='margin-bottom:0px!important;'" : "";
    this.targetRender = targetRender;
    this.baseClass = 'component_editor_pizza';
    this.allowedOptions = allowedOptions;
    this.showEdges = (!listEdges || listEdges.length == 0) || (this.dataItem.item_borda != undefined && this.dataItem.item_borda != false && this.dataItem.item_borda.length > 0) ? "" : " style='display: none;' " ;
    this.showObservations = (!listObservations || listObservations.length == 0) || (this.dataItem.item_observacoes != undefined && this.dataItem.item_observacoes != false && this.dataItem.item_observacoes.length > 0) ? "" : " style='display: none;' " ;
    this.instanceHash = (Math.random() + 1).toString(36).substring(4);
    this.showHand = true;
    this.showBtnFinishCombo = targetRender.indexOf('combo') > -1 ? true : false;
    this.showTotalPrice = showTotalPrice;
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
    if (typeof editorGenericCurrent != "undefined") editorGenericCurrent = null;
    this.setListSizes();
    this.setListFlavors();
    this.setListDough();
    this.setListEdges();
    this.setListObservations();

    const itemInEditing = $('#itemInEditing').val();
    let sessionItemData = sessionStorage.getItem('itemEditingED');

    if (sessionItemData && itemInEditing) {
      sessionItemData = JSON.parse(sessionItemData);
      itemEditing = sessionItemData;
    } else {
      sessionStorage.removeItem('itemEditingED');
      this.setDough();
      this.setEdges();
      this.setObservations();
      this.setIngredients();
    }
      
    $(this.targetRender).html(this.getRender());
    setConfigItem();
    this.renderFlavors();
    this.renderItemEdge();
    this.renderItemDough();
    this.renderItemObservations();
    this.renderItemExtraInfo();
    $(".updateSize").select2({
      language: "pt-BR",
      minimumResultsForSearch: Infinity
    });
    
    setTimeout(function(){
      descer(subir);
    }, 100);

    $('.btnFinishEditorPizza').addClass(`${this.baseClass}_btn_finish_action`);
    $('.btnFinishEditorPizza').parent().addClass(this.instanceHash);

    const thisClass = this;
    $(document).on('click', `.${thisClass.instanceHash} #pizzaNumberFlavorsAdd`, function(e){
      thisClass.updatePizzaNumberFlavors('add');
    });
  
    $(document).on('click', `.${thisClass.instanceHash} #pizzaNumberFlavorsRemove`, function(e){
      thisClass.updatePizzaNumberFlavors('remove');
    });

    $(document).on("change", `.${thisClass.instanceHash} .updateSize`, function (e) {  
      const sizeId = $(this).val();
      const data = {
        tamanho: sizeId
      };

      const action = "alterar";
      updateSize(thisClass.dataItemCurrent, data, action);
    });

    $(document).on("click", `.${thisClass.instanceHash} .${thisClass.baseClass}_remove_flavor`, function(e){
      const flavorId = $(this).data('flavorid');
      const slice = $(this).data('slice');
      removeFlavor(thisClass.dataItemCurrent, flavorId, slice);
    });

    $(document).on("click", `.${thisClass.instanceHash} .${thisClass.baseClass}_btn_finish_action`, async function(e){
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
      
      const upsellItemsAdd = await getUpsellItemsProduct();
      if (upsellItemsAdd) thisClass.dataItemCurrent.upsell = upsellItemsAdd;

      thisClass.dataItemCurrent["dough"] = JSON.stringify(itemEditing["dough"]);
      thisClass.dataItemCurrent["edges"] = JSON.stringify(itemEditing["edges"]);
      thisClass.dataItemCurrent["observations"] = JSON.stringify(itemEditing["observations"]);
      thisClass.dataItemCurrent["ingredients"] = JSON.stringify(itemEditing["ingredients"]);

      const urlRedir = typeof urlredir != "undefined" ? urlredir : null;

      addCustomItem(thisClass.dataItemCurrent, null, urlRedir);
    });

    $(document).on("click", `.${thisClass.instanceHash} .${thisClass.baseClass}_edit_ingredients`, function(e){
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
    
    updateTotalItem();
  }

  getRender(){
    return `
      <div style="background: none!important;" id="${this.baseClass}_container" class="${this.instanceHash} ${this.baseClass}_type_editor_${this.typeEditor}" data-dadositem='${JSON.stringify(this.dataItem)}'  data-dadosdoitematual='${JSON.stringify(this.dataItemCurrent)}'>
        <div class="${this.baseClass}_buttons_actions" id="${this.baseClass}_buttons_actions">
          <span class='lbl_drop_montador'>Tamanho:</span>
          <select class='drop_montador updateSize' id="dropPizzaSize">
            ${this.renderSizes()}
          </select>
          <div class="btn_montador_rounded" id="pizzaNumberFlavors">
            <button class="btn_left" id="pizzaNumberFlavorsRemove">
              <i class="material-icons">remove</i>
            </button>
            <span id="pizzaNumberFlavorsValue">
              ${this.renderNumberFlavors()}
            </span>
            <button class="btn_right" id="pizzaNumberFlavorsAdd">
              <i class="material-icons">add</i>
            </button>
          </div>
        </div>
        <section class="container clearfix ${this.baseClass}_div_editor">
          <section class="coluna col-pizza">
            ${this.renderEditorPizza()}
            <div id="maozinha">
              <div class="cont_balao">
                <img src="${this.urlImageHand}" />
              </div>
            </div>
          </section>
        </section>
        ${!this.showTotalPrice ? "" : `<span class="total_pizza">Preço da Pizza: R$ 0,00</span>`}
        <div class="${this.baseClass}_componentsPizza">
          <div id="btns_complementos">
            <button id="pizzaEdges" class="openModalEdges btn_montador_rounded opcionais" ${this.showEdges}><i class="material-icons">star</i> Escolher ${this.edgeName}</button>
            <button id="pizzaObservations" class="openModalObservations btn_montador_rounded opcionais"><i class="material-icons">chat</i> Observações</button>
          </div>
          <div id="areanomesabores">
          </div>
          <div id="areabordas">
          </div>
          <div id="areamassa">
          </div>
          <div id="areaobservacoes">
          </div>
          ${!this.allowedExtraInfo ? "" : `<textarea rows='3' maxlength=140 minlength=3 id='obs_item' placeholder='Alguma observação?' class='inputCampo2' ${this.marginExtraInfo}></textarea>`}
        </div>
        ${this.htmlUpsell}
      </div>
      ${!this.showBtnFinishCombo ? "" : `
      <div class="${this.baseClass}_div_btn_finish ${this.instanceHash}">
        <div class="${this.baseClass}_btn_finish ${this.baseClass}_btn_finish_action">
          <p><i class="material-icons">shopping_cart</i> Pronto! Voltar ao Combo</p>
        </div>
      </div>`}
      <div class="${this.baseClass}_backdrop backdrop"></div>
      <div class="modal fade ${this.baseClass}_modalEddy modalEddy" tabindex="-1" aria-labelledby="itemModal" aria-hidden="true"></div>
    `;
  }

  renderEditorPizza(){
    const domainMedia = urlsfiles["media"];
    let backgroungImg = '';
  
    const quantityFlavor = this.getQuantityFlavorBySize(this.dataItem.item_tamanhoid);
    let numberFlavorsItem = quantityFlavor.filter(x => parseInt(x) == parseInt(this.dataItem.item_qtdsabor) || parseInt(x) > parseInt(this.dataItem.item_qtdsabor))[0];
    if (!numberFlavorsItem) {
      numberFlavorsItem = quantityFlavor.slice(-1);
    }
    
    let html = '<div class="areapizza ">';
    let html2 = "";
    if(numberFlavorsItem == 1){
      html2 += `<span class="icones removesabor umsabor ${this.baseClass}_remove_flavor " data-target-combo="" data-flavorid=""  data-slice="1" style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`;
      html+= '<div class="pztop-abs pzinteira"  style="background-position: top left;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-slice="1" data-pdc="1" data-qtdsabores="1"></span>`
        +    '</div>';
      backgroungImg =`${domainMedia}0.01.001/img/${this.imgBackgroundPizza}_1.png`;
    }else if(numberFlavorsItem == 2){
      html2 += `<span class="icones removesabor doissabores-esq ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="1" data-flavorid=""  style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
              + `<span class="icones removesabor doissabores-dir ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="2" data-flavorid=""  style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`;
      html+= '<div class="pztop-abs metade_esq"  style="background-position: top left;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-slice="1" data-pdc="1" data-qtdsabores="2"></span>`
        +    '</div>';
      html+= '<div class="pztop-abs metade_dir"  style="background-position: top right;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-slice="2" data-pdc="2" data-qtdsabores="2"></span>`
        +    '</div>';
      backgroungImg =`${domainMedia}0.01.001/img/${this.imgBackgroundPizza}_2.png`;
    }else if(numberFlavorsItem == 3){
      html2 += `<span class="icones removesabor tressabores-esq ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="1" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
          + `<span class="icones removesabor tressabores-meio ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="2" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
          + `<span class="icones removesabor tressabores-dir ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="3" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`;
      html+= '<div class="pztop-abs tres_esq" > '
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-slice="1" data-pdc="1" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-qtdsabores="3"></span>`
        +    '</div>';
      html+= '<div class="pztop-abs tres_dir"  style="background-position: right bottom;" >'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-slice="3" data-pdc="3" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-qtdsabores="3"></span>`
        +    '</div>';
      html+= '<div class="pztop-abs tres_meio" >'
        +        '<div class="bgtaboa"></div>'
        +        `<span class="fotosabmeio ${this.typeEditor}" data-target-combo="" >`
        +            `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-slice="2" data-pdc="2" data-tamanhopizza="${this.dataItem.item_tamanhoid}" data-qtdsabores="3"></span>`
        +        '</span>'
        +    '</div>';
      backgroungImg =`${domainMedia}0.01.001/img/${this.imgBackgroundPizza}_3.png`;
    }else if(numberFlavorsItem == 4){
      html2 += `<span class="icones removesabor quatrosab-top-esq ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="1" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
          + `<span class="icones removesabor quatrosab-top-dir ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="2" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
          + `<span class="icones removesabor quatrosab-bott-esq ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="3" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`
          + `<span class="icones removesabor quatrosab-bott-dir ${this.baseClass}_remove_flavor " data-target-combo="" data-slice="4" data-flavorid=""   style="display: none;" title="Remover sabor"><i class="material-icons">cancel</i></span>`;
      html+= '<div class="pztop-abs quarto_esq_cima" style="background-position: top left;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${+this.dataItem.item_tamanhoid}" data-slice="1" data-pdc="1" data-qtdsabores="4"></span>`
        +    '</div>'
        +    '<div class="pztop-abs quarto_dir_cima" style="background-position: top right;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${+this.dataItem.item_tamanhoid}" data-slice="2" data-pdc="2" data-qtdsabores="4"></span>`
        +    '</div>'
        +	'<div class="quarto_esq_baixo" style="background-position: bottom left;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${+this.dataItem.item_tamanhoid}" data-slice="3" data-pdc="3" data-qtdsabores="4"></span>`
        +    '</div>'
        +    '<div class="quarto_dir_baixo" style="background-position: bottom right;">'
        +        `<span class="linkpizza ${this.baseClass}_open_list_flavors openModalFlavors" data-target-combo="" data-flavorid="0" data-tamanhopizza="${+this.dataItem.item_tamanhoid}" data-slice="4" data-pdc="4" data-qtdsabores="4"></span>`
        +    '</div>';
      backgroungImg =`${domainMedia}0.01.001/img/${this.imgBackgroundPizza}_4.png`;
    }

    html+= "</div>";
    html= html2 + html;
        
    $(".openModalEdges").show();
    if(this.edges.length == 0){
      $(".openModalEdges").hide();
    }else if(this.dataItem.item_massa != undefined){
      if(this.dataItem.item_massa.item_massaaceitaborda == "N"){
        $(".openModalEdges").hide();
      }
    }
    $(".openModalObservations").show();
    if(this.observations.length == 0){
      $(".openModalObservations").hide();
    }
    
    $(".openmodalqtdsabores").show();
    if(quantityFlavor.length == 1){
      $(".openmodalqtdsabores").hide();
    }
    
    return html = `
      <div class="formapizza" style="background-image: url(${backgroungImg})">
        ${html}
      </div>
    `;
  }

  renderFlavors(){
    const domainImages = urlsfiles["imagens"];
    let flavors = this.dataItem.sabores;
    let html = "";

    for(let sb = 0; sb < flavors.length; sb++){
      const slice = flavors[sb].item_saborpedaco;
      const flavorId = flavors[sb].item_saborid;
      const flavorName = flavors[sb].item_sabornome;
      const imgId = flavors[sb].item_saborfotoid;
      const imgName = flavors[sb].item_saborfotonome;
      const img = `${domainImages}produtos/${imgId}/240/${imgName}`;
      
      html += "<span class='lblsabor'>"
      +    `<span class='${this.baseClass}_btn_remove_flavor ${this.baseClass}_remove_flavor removeFlavor' title='Excluir Sabor' data-slice='${slice}' data-flavorid='${flavorId}'><i class='material-icons'>cancel</i></span>`
      +    `<a href='#' class='lbldesc vering ${this.baseClass}_editFlavor ${this.baseClass}_edit_ingredients' title='Editar Ingredientes' data-slice='${slice}' data-flavorid='${flavorId}' data-nomesabor='${flavorName}' ><div class='descriptionFlavor'>${flavorName}</div><i class='material-icons'>edit</i></a>`
      + "</span>";
      
      if($(".linkpizza[data-slice='"+slice+"']").length === 1){
        $(".icones.removesabor[data-slice='"+slice+"'] ").css("display","inline");
        $(".icones.removesabor[data-slice='"+slice+"'] ").data("flavorid",flavorId);
        
        
        const slicePizza = $(".linkpizza[data-slice='"+slice+"']");
        slicePizza.removeClass("openlistasabores");
        slicePizza.removeClass("component_editor_pizza_open_list_flavors");
        slicePizza.removeClass("openModalFlavors");
        slicePizza.addClass(`${this.baseClass}_edit_ingredients`);
        
        slicePizza.data("flavorid", flavorId);
        slicePizza.attr("title", flavorName);
        
        const bgped = slicePizza.parent();
        
        if(img !== null){
          bgped.css({"background-image":"url("+img+")"});
        }
      }
    }
    
    if(isMobile && flavors.length == 1 && typeof showTourPt2 != "undefined"){
      showTourPt2();
    }

    $('#areanomesabores').html(html);
  }

  renderNumberFlavors(){
    const sizeId = this.dataItem.item_tamanhoid;
    const numberFlavors = this.getQuantityFlavorBySize(sizeId);
    let numberFlavorsItem = parseInt(this.dataItem.item_qtdsabor);
    
    numberFlavorsItem = numberFlavors.filter(x => parseInt(x) == parseInt(numberFlavorsItem) || parseInt(x) > parseInt(numberFlavorsItem))[0];
    if (!numberFlavorsItem) {
      numberFlavorsItem = numberFlavors.slice(-1);
    }
  
    let textNumber = parseInt(numberFlavorsItem) > 1 ? "sabores" : "sabor";
    return `${numberFlavorsItem} ${textNumber}`
  }

  updatePizzaNumberFlavors(action) {
    const sizeId = this.dataItem.item_tamanhoid;
    const numberFlavors = this.getQuantityFlavorBySize(sizeId).map(x => parseInt(x));
    let numberFlavorsItem = parseInt(this.dataItem.item_qtdsabor);
  
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
    updateNumberFlavors(this.dataItemCurrent, data, updateAction);
  }

  updateEditor(){
    $(this.targetRender).html(this.getRender());
    if (!this.showHand) {
      $("#maozinha").hide();
    }
    setConfigItem();
    this.renderItemEdge();
    this.renderItemDough();
    this.renderItemObservations();
    this.renderFlavors();
    this.renderItemExtraInfo();
    $(".updateSize").select2({
      language: "pt-BR",
      minimumResultsForSearch: Infinity
    });

    this.updateIngredientsAddItemEditing();
    updateTotalItem();
  }

  renderItemEdge(){
    if ($("#areabordas").length == 0) return;
    
    if (this.edges.length == 0) {
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
    
    const nameEdge = this.edges.length > 0 ? this.edges[0]["borda_nome"].split(':')[0] : 'Borda';
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

  renderItemDough(){
    const list = typeof editorPizzaCurrent != "undefined" ? editorPizzaCurrent.dough : listDough;
    if (this.dough.length == 0) return;
  
    let nameDough = "Massa";
    if (this.dough.length > 0) {
      nameDough = this.dough[0]["name"] ? this.dough[0]["name"].split(':')[0] : this.dough[0]["massa_nome"].split(':')[0];
    }
  
    let html = "";
    const dough = itemEditing.dough;
    if(dough != undefined && dough != false && $("#areamassa").length > 0){
      html = "<span class='lblsabor'>"
      +    "<span class='removeDough' title='Alterar "+nameDough+"'><i class='material-icons'>cancel</i></span>"
      +    "<a class='lbldescopt openModalDough descriptionEditEdges' title='"+dough.name+"'><div class='descriptionDough'>"+ nameDough + ': ' + dough.name+"</div><i class='material-icons'>edit</i></a>"
      +"</span>";
    }
    
    const getDough = this.dough.find(x => (x["id"] ?? x["massa_id"]) == dough["id"]);
    if (getDough && getDough['allowsEdge'] == "N") {
      itemEditing.edges = [];
      this.renderItemEdge();
      $('#pizzaEdges').hide();
    } else {
      if (itemEditing.edges.length == 0 && this.edges.length > 0) {
        $('#pizzaEdges').show();
      }
    }
    
    $("#areamassa").html(html);
  }
  
  renderItemObservations(){
    if ($("#areaobservacoes").length == 0) return;
  
    if (this.observations.length == 0) {
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
}
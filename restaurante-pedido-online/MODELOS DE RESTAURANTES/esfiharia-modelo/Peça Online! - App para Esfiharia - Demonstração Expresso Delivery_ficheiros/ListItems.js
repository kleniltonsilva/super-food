class ListItems {
  constructor(type, title, description, info, items = []) {
    this.type = type;
    this.title = title;
    this.description = description || "";
    this.info = info || {};
    this.list = this.formatListItems(items);
    this.domainImage = 'https://static.expressodelivery.com.br/imagens';
    this.baseClass = 'component_list_items';
  }

  formatListItems(listItems){
    const schema = {
      'sabor_id': 'itemId',
      'sabor_nome': 'itemName',
      'sabor_descricao': 'itemDescription',
      'sabor_sessaonome': 'itemSessionName',
      'sabor_sessaoid': 'itemSessionId',
      'sabor_image': 'itemImage',
      'sabor_fotonome': 'itemImageName',
      'sabor_fotoid': 'itemImageId',
      'sabor_preco': 'itemPrice',
      'sabor_precopromo': 'itemPricePromo',
      'sabor_ingredientes': 'itemIngredients',
      'sabor_estoque': 'itemStock',
      'sabor_sessao_controlarestoque': 'itemControlStock',
      'sabor_tag': 'itemTag',
      'sabor_tagcor': 'itemTagColor',
      'sabor_tag_nome': 'itemTag',
      'sabor_tag_cor': 'itemTagColor',
      'sessao_bgitem' : 'itemImageBackgroundId',
      'sessao_fotobgnome' : 'itemImageBackgroundName',
      'sizeName': 'itemName',
      'sizePricePromo': 'itemPrice',
      'price': 'itemPrice',
      'sizeId': 'itemId',
      'sessao_layout_texto': 'itemLayoutDescription'
    }

    const convert = (data, schema) => {
      for (let i = 0; i< data.length; i++) {
        const item = data[i];
        const newObject = {};
        for (const key in item) {
          if (item.hasOwnProperty(key)) {
            const keyFormated = schema[key] || key;
            newObject[keyFormated] = item[key];
          }
        }
        data[i] = newObject;
      }

      return data;
    }

    return convert(listItems, schema);
  }

  getRender(){
    const thisClass = this;
    let htmlCardsItems = '';

    for (let item of this.list) {
      const itemId = item['itemId'] ?? '';
      const itemLayoutDescription = item['itemLayoutDescription'] ?? '';
      let itemName = item['itemName'] ?? '';
      let itemDescription = itemLayoutDescription.indexOf('desc') > -1 && item['itemDescription'] ? item['itemDescription'] : '';
      const itemSessionId = item['itemSessionId'] ?? '';
      const itemSessionName = item['itemSessionName'] ?? '';
      const itemImageName = item['itemImageName'] ?? false;
      const itemImageId = item['itemImageId'] ?? '';
      const itemImage = item['itemImage'] ?? null;
      const itemImageBackgroundId = item['itemImageBackgroundId'] ?? false;
      const itemImageBackgroundName = item['itemImageBackgroundName'] ?? '';
      let itemImageUrl = "";
      if (itemImage) {
        itemImageUrl = `${this.domainImage}/itens/${itemImage}`;
      } else if (itemImageName) {
        itemImageUrl = `${this.domainImage}/produtos/${itemImageId}/180/${itemImageName}`;
      }

      let itemImageBackgroundUrl = "";
      if (itemImageBackgroundName) {
        itemImageBackgroundUrl = `${this.domainImage}/produtos/${itemImageBackgroundId}/96/${itemImageBackgroundName}`;
      }

      const itemSizeId = item['itemSizeId'] ?? false;
      const itemControlStock = item['itemControlStock'] && item['itemControlStock'] == 'S' ? true : false;
      const itemStock = item['itemStock'] ?? 0;
      const itemUnavailable = itemControlStock && parseInt(itemStock) <= 0 ? ' item_indisponivel ' : '';
      let itemSizeName = '';
      const itemIngredients = item['itemIngredients'] ?? false;
      const itemQuantity = item['itemQuantity'] ?? false;
      const itemTag = item['itemTag'] ?? false;
      const itemTagColor = item['itemTagColor'] ?? false;
      const urlEditor = this.info["urlEditor"] ?? null;
      const price = item['itemPrice'] ? item['itemPrice'] : '';
      const pricePromo = item['itemPricePromo'] ?? '';
      let itemPrice = price != '' ? `+ R$ ${parseReal(price)}` : '';
      if (price != "" && pricePromo != "" && parseFloat(pricePromo) < parseFloat(price)) {
        itemPrice = `+ <span class="${this.baseClass}_pricefull">R$ ${parseReal(price)}</span> <span class="${this.baseClass}_pricepromo">R$ ${parseReal(pricePromo)}</span>`;
      }
      if (this.type == 'comboItem' || this.type == 'comboItemReadyCustomizable') {
        itemPrice = item?.itemAddValue && item.itemAddValue > 0 ? `+ R$ ${parseReal(item.itemAddValue)}` : "";
      }
      let buttonSelectorItem = '';
      let itemIngredientsText = null;
      let itemQuantityText = null;
      let itemTagText = null;
      let buttonDeleteItem = '';
      let dataInfo = '';
      const codConf = this.info['comboData'] ? this.info['comboData']['data_codconfcombo'] ?? '' : '';

      if (this.type == "modalFlavors") {
        if (itemIngredients && itemLayoutDescription.indexOf('ing') > -1) {
          itemIngredientsText = '';
          itemIngredients.forEach(x => {
            itemIngredientsText += `${x['sabor_ingrediente_nomeingrediente']}, `;
          });

          itemIngredientsText = itemIngredientsText.slice(0, -2);
        }
      }

      if (this.type == 'comboItem' || this.type == 'comboItemReadyCustomizable') {
        if (this.type == 'comboItem' && urlEditor != 'new') {
          if (item['sabor_precostamanhos']) {
            const getSizeInfo = item['sabor_precostamanhos'].filter(x=> x['sabor_precotamanhos_codtamanho'] == itemSizeId);
            if (getSizeInfo.length > 0) {
              itemSizeName = `(${getSizeInfo[0]['sabor_precotamanhos_nometamanho']})`;
            }
          }
        } else {
          itemSizeName = `(${item['itemName']})`;
        }
        
        if(this.info['allowsEditing']) {
          const urlEditor = this.info["urlEditor"] ?? null;
          buttonSelectorItem = this.buttonSelectorEditor(urlEditor);

          if (itemIngredients && itemLayoutDescription.indexOf('ing') > -1) {
            itemIngredientsText = '';
            itemIngredients.forEach(x => {
              itemIngredientsText += `${x['sabor_ingrediente_nomeingrediente']}, `;
            });

            itemIngredientsText = itemIngredientsText.slice(0, -2);
          }

          if (this.type == 'comboItemReadyCustomizable' || urlEditor == 'new') {
            itemDescription = getHtmlDetailsItemCustomizableCombo(item['itemData']);
            itemName = item["itemFlavors"].join(', ');
            if (!itemImageId) itemImageUrl = itemImageName;
            buttonDeleteItem = item['itemData']['hashItemCombo'] ? this.buttonDeleteItem(item['itemData']['hashItemCombo']) : '';
          }
        } else {
          if (this.info['allowedQuantity'] > 1) {
            buttonSelectorItem = this.buttonSelectorQuantity(itemId, itemName, itemSessionId, itemSessionName, price, itemSizeId);
          } else {
            buttonSelectorItem = this.buttonSelectorRadio(itemId, itemSessionId, price, itemSizeId, itemQuantity);
          }
        }

        if (itemQuantity) {
          itemQuantityText = parseInt(itemQuantity) > 1 ? `${itemQuantity} Unidades` : '1 Unidade';
        }
      }

      if (this.type == "modalAddItemSizes" || this.type == "modalDough") {
        if (this.type == "modalDough" && parseFloat(price) == 0) itemPrice = "";
    
        buttonSelectorItem = this.buttonSelectorRadio(itemId, null, price, null, null, itemName);
      }

      if (this.type == "modalAddItemSizes" || this.type == "modalFlavors") {
        itemPrice = itemPrice.replace('+ ', '');
      }

      if (this.type == "modalObservations" || (this.type == "modalEdges" && this.info["typeSelector"] == "checkbox") || (this.type == "modalIngredients" && this.info["typeSelector"] == "checkbox")) {
        if (parseFloat(price) == 0) itemPrice = "";
        buttonSelectorItem = this.buttonSelectorCheckbox(itemId, null, price, null, itemName);
      }

      if (this.type == "modalEdges" && this.info["typeSelector"] == "radio") {
        if (parseFloat(price) == 0) itemPrice = "";
        buttonSelectorItem = this.buttonSelectorRadio(itemId, null, price, null, null, itemName);
      }

      if (this.type == "buyAndGet") {
        itemDescription = `
          <span class="buyAndGetDetailsItem">
            ${item["itemDescription"]}
          </span>
        `

        dataInfo = ` data-refpromo='${this.info['itemRefPromo']}' `;
        buttonSelectorItem = this.buttonSelectorRadio(itemId, null, null, null, null, null);
      }
      
      if (this.type == "modalIngredientsAdd") {
        const typeSelector = this.info["typeSelector"];

        if (typeSelector == "checkbox") {
          buttonSelectorItem = this.buttonSelectorCheckbox(itemId, null, price, null, itemName);
        }

        if (typeSelector == "quantity") {
          buttonSelectorItem = this.buttonSelectorQuantity(itemId, itemName, null, null, price, null);
        }
      }

      if (itemTag && itemTagColor) {
        itemTagText = `<span class="tag_prod ${this.type}_${this.baseClass}_tag" style="background-color: ${itemTagColor}">${itemTag}</span>`;
      }

      let htmlItem = '';
      let classEditor = '';
      if (this.info['allowsEditing']) {
        classEditor = ` ${this.baseClass}_selector_editor_card_${this.type} `;
        let comboData = typeof this.info['comboData'] == 'string' ? JSON.parse(this.info['comboData']) : this.info['comboData'];
        comboData['data_itemsabor'] = itemId;
        comboData['data_itemtamanho'] = itemSizeId;
        dataInfo = ` data-itemdata='${JSON.stringify(comboData)}' `;
        if (urlEditor && urlEditor != 'new') {
          dataInfo += `data-urleditor='${urlEditor}' `
        }
      }
      

      htmlItem += `
        <label class='mdl-list__item ${this.baseClass}_item ${this.type}_${this.baseClass}_item ${itemUnavailable} ${classEditor}' data-${this.type}-itemid='${itemId}' ${dataInfo} data-codconf='${codConf}' for='list-${this.type}-${itemId}' data-name="${itemName}">
          <div class="${this.baseClass}_item_info">
            ${itemImageUrl ? `
              <div class="${this.baseClass}_image_background">
              ${itemImageBackgroundUrl ? `
                <img class="${this.baseClass}_background_image" itemprop="image" src="${itemImageBackgroundUrl}" class="img_expandido" loading="lazy">  
                `: ""}
                <img class="${this.baseClass}_image" itemprop="image" src="${itemImageUrl}" class="img_expandido" loading="lazy">
              </div>
            `: ""}
            <div class="${this.baseClass}_name_description">
            <div class="${this.baseClass}_div_name">
            <p itemprop="name" class="${this.baseClass}_name">${itemName} ${itemSizeName} ${itemPrice}</p>
            ${buttonDeleteItem}
            </div>
              ${itemDescription ? `<p class="${this.baseClass}_description">${itemDescription}</p>` : ''}
              ${itemIngredientsText ? `<p class="${this.baseClass}_ingredients">${itemIngredientsText}</p>` : ''}
              ${itemQuantityText ? `<p class="${this.baseClass}_ingredients">${itemQuantityText}</p>` : ''}
              ${itemTagText ? itemTagText : ''}
            </div>
          </div>
          <div class="${this.baseClass}_selector">
            ${buttonSelectorItem}
          </div>
        </label>
      `;

      htmlCardsItems += htmlItem;
    }

    const html = `
      <ul class="list_ing mdl-list">
        ${!this.title ? '' : `
          <li class="tit_ing">    
            <div class="${this.baseClass}_info">
              <div class="${this.baseClass}_info_title">
                <i class='material-icons'>keyboard_arrow_down</i> 
                ${this.title}
              </div>
              <div class="${this.baseClass}_info_description">
                ${this.description}
              </div>
            </div>
          </li>  
        `}
        ${htmlCardsItems}
      </ul>
    `;


    setTimeout(function(e){
      Array.from($(`.${thisClass.baseClass}_selector_radio_label`)).map(element => {
        $(element).parent().parent().attr('for', $(element).prop('for'));
      });

      Array.from($(`.${thisClass.baseClass}_selector_checkbox_label`)).map(element => {
        $(element).parent().parent().attr('for', $(element).prop('for'));
      });
    }, 500)

    return html;
  }

  buttonSelectorQuantity(itemId, itemName, itemSessionId, itemSessionName, price, itemSizeId){
    const codConf = this.info['comboData'] ? this.info['comboData']['data_codconfcombo'] ?? '' : '';
    const max = this.info["max"] ?? null;
    const maxPer = this.info["maxPer"] ?? null;
    return `
      <div class='${this.baseClass}_btn_quantity_card'>
        <span class='${this.baseClass}_quantity_decrease ${this.type}_quantity_decrease' data-itemid='${itemId}' data-combocodconf="${codConf}" data-comboallowedquantity="${this.info['allowedQuantity']}" data-sizeid="${itemSizeId}">-</span>
        <input class='${this.baseClass}_quantity_value ${this.type}_quantity_value inteiro' data-itemid='${itemId}' data-itemname='${itemName}' data-price='${price}' data-sessionname='${itemSessionName}' data-combocodconf="${codConf}" data-comboallowedquantity="${this.info['allowedQuantity']}" data-sizeid="${itemSizeId}" value="0" type="number" maxlength='3' data-max="${max}" data-maxper="${maxPer}">
        <span class='${this.baseClass}_quantity_increase ${this.type}_quantity_increase' data-${this.type}-sessionid='${itemSessionId}' data-itemid='${itemId}' data-combocodconf="${codConf}" data-comboallowedquantity="${this.info['allowedQuantity']}" data-sizeid="${itemSizeId}">+</span>
      </div>
    `;
  }

  buttonSelectorRadio(itemId, itemSessionId, itemPrice, itemSizeId, itemQuantity, itemName){
    const dataItemQuantity = itemQuantity ? `data-quantity="${itemQuantity}"` : '';
    let codConf = this.info['comboData'] && this.info['comboData']['data_codconfcombo'] ? this.info['comboData']['data_codconfcombo'] : '';

    if (this.type == "buyAndGet") {
      codConf = this.info["itemRefPromo"];
    }

    const codConfText = codConf ? `_${codConf}` : '';
    let propId = itemSizeId ? `${this.baseClass}_${this.type}_radio_item_${itemId}_${itemSizeId}` : `${this.baseClass}_${this.type}_radio_item_${itemId}`;
    propId = codConf ? `${propId}_${codConf}` : propId;

    return `
      <label class='mdl-radio mdl-js-radio ${this.baseClass}_selector_radio_label' for='${propId}'>
        <input type='radio' id='${propId}' name='${this.baseClass}_selector_radio_${itemSessionId}_${codConfText}' class='mdl-radio mdl-radio__button ${this.baseClass}_selector_radio_input ${this.type}_selector_radio_input' value='${itemId}' data-price='${itemPrice}' data-sessionid='${itemSessionId}' data-combocodconf="${codConf}" data-sizeid="${itemSizeId}" ${dataItemQuantity} data-name="${itemName}">
        <span class='mdl-radio__label'></span>
      </label>
    `;
  }


  buttonSelectorCheckbox(itemId, itemSessionId, itemPrice, itemSizeId, itemName){
    const codConf = this.info['comboData'] && this.info['comboData']['data_codconfcombo'] ? this.info['comboData']['data_codconfcombo'] : '';
    const codConfText = codConf ? `_${codConf}` : '';
    let addType = this.type == "modalIngredientsAdd" ? "_modalIngredientsAdd" : "";
    let propId = itemSizeId ? `${this.baseClass}_${this.type}_radio_item_${addType}${itemId}_${itemSizeId}` : `${this.baseClass}_${this.type}_radio_item_${addType}${itemId}`;
    propId = codConf ? `${propId}_${codConf}` : propId;

    const max = this.info["max"] ?? null;
    const maxPer = this.info["maxPer"] ?? null;

    return `
      <label class='mdl-checkbox mdl-js-checkbox ${this.baseClass}_selector_checkbox_label' for='${propId}'>
        <input type='checkbox' id='${propId}' name='${this.baseClass}_selector_checkbox_${itemSessionId}_${codConfText}' class='mdl-checkbox mdl-checkbox__input ${this.baseClass}_selector_checkbox_input ${this.type}_selector_checkbox_input' value='${itemId}' data-price='${itemPrice}' data-sessionid='${itemSessionId}' data-combocodconf="${codConf}" data-sizeid="${itemSizeId}" data-name="${itemName}" data-max="${max}" data-maxper="${maxPer}">
        <span class='mdl-checkbox__label'></span>
      </label>
    `;
  }

  buttonSelectorEditor(urlEditor = null){
    const icon = urlEditor ? 'edit' : 'add';

    return `
      <button class='${this.baseClass}_selector_editor mdl-button mdl-js-button'>
        <i class='material-icons'>${icon}</i>
      </button>
    `;
  }

  buttonDeleteItem(itemId){
    let dataCodConfCombo = this.info['comboData']['data_codconfcombo'] ? `data-combocodconf="${this.info['comboData']['data_codconfcombo']}"` : '';
    return `
      <span class="${this.baseClass}_remove_item ${this.baseClass}_remove_item_${this.type}" data-itemId="${itemId}" ${dataCodConfCombo}>
        <span class="material-icons">close</span>
      </span>
    `;
  }
}
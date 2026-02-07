class Editor{
  constructor(){
    this.sizes = [];
    this.flavors = [];
    this.edges = [];
    this.dough = [];
    this.observations = [];
    this.extraInfoCurrent = "";
  }

  setListSizes(){
    this.sizes = listSizes;
    if (this.allowedOptions && this.allowedOptions?.sizes) {
      const sizes = [];
      for (const size of this.allowedOptions.sizes) {
        let findSize = listSizes.find(x => x['tamanho_id'] == size["ID"]);
        if (findSize) {
          sizes.push({
            ...findSize,
            tamanho_qtdsabormaxima: (() => {
              if (findSize?.tamanho_qtdmaxsabores)  {
                findSize["lista_qtdsabor"] = Array.isArray(findSize.tamanho_qtdmaxsabores) ? findSize.tamanho_qtdmaxsabores : JSON.parse(findSize.tamanho_qtdmaxsabores);
                delete findSize.tamanho_qtdmaxsabores;
              }

              const array = [];
              for (let i = 1; i <= size["QTDMAX"]; i++) {
                if (findSize["lista_qtdsabor"].find(x => (x["value"] || x).toString() == i.toString())) {
                  array.push(i.toString());
                }
              }
              return array;
            })()
          });
        }
      }

      this.sizes = sizes;
    }
  }

  setListFlavors(){
    this.flavors = listFlavors;
    if (this.allowedOptions && (this.allowedOptions?.items || this.allowedOptions?.SABORES)) {
      const flavors = [];
      for (const flavor of this.allowedOptions.items || this.allowedOptions["SABORES"]) {
        let findFlavor = listFlavors.find(x => x['sabor_id'] == (flavor["itemId"] || flavor["sabor_id"] || flavor));
        if (findFlavor) {
          flavors.push(findFlavor);
        }
      }

      this.flavors = flavors;
    }
  }

  setListEdges(){
    this.edges = [];
    const typeCharge = this.allowedOptions ? this.allowedOptions["options"]["BORDAS"]["COBRAR"] : null;
    if (typeCharge == "NP") return;

    const sizeId = this.dataItem.item_tamanhoid;
    const edges = [];
    for (const edge of listEdges) {
      let getBySize = null;
      if (edge?.borda_precotamanho) {
        getBySize = edge["borda_precotamanho"].find(x => x["precotamannho_tamanhoid"] == sizeId);
        if (!getBySize) continue;
      }

      const price = typeCharge == "N" ? 0 : getBySize && getBySize["precotamannho_preco"] ? getBySize["precotamannho_preco"] : edge["borda_preco"];
      edges.push({
        ...edge,
        borda_id: edge["borda_id"],
        borda_nome: edge["borda_nome"],
        borda_ordem: edge["borda_ordem"],
        borda_preco: price
      })
    }

    this.edges = edges;
  }

  setListDough(){
    this.dough = []
    const sizeId = this.dataItem.item_tamanhoid;
    const doughs = [];

    for (const dough of listDough) {
      if (!dough?.massa_precotamanho) {
        doughs.push(dough);
        continue;
      }

      const getBySize = dough["massa_precotamanho"].find(x => x["precotamannho_tamanhoid"] == sizeId);
      if (!getBySize) continue;

      doughs.push({
        ...dough,
        id: dough["massa_id"],
        name: dough["massa_nome"],
        order: dough["massa_ordem"],
        price: getBySize["precotamannho_preco"],
        allowsEdge: dough["allowsEdge"]
      })
    }

    this.dough = doughs;
  }

  setListObservations(){
    this.observations = []

    const typeCharge = this.allowedOptions ? this.allowedOptions["options"]["OBSERVASOES"]["COBRAR"] : null;
    if (typeCharge == "NP") return;

    const sizeId = this.dataItem.item_tamanhoid;
    const observations = [];

    for (const observation of listObservations) {
      let getBySize = null;

      if (observation?.observacoes_precotamanho) {
        const getBySize = observation["observacoes_precotamanho"].find(x => x["precotamannho_tamanhoid"] == sizeId);
        if (!getBySize) continue;
      }

      const price = typeCharge == "N" ? 0 : getBySize && getBySize["precotamannho_preco"] ? getBySize["precotamannho_preco"] : observation["price"];
      observations.push({
        ...observation,
        id: observation["observacoes_id"],
        name: observation["observacoes_nome"],
        order: observation["observacoes_ordem"],
        price: price
      })
    }

    this.observations = observations;
  }

  setDough() {
    if (this.dataItem["item_massa"] && this.dough.length > 0) {
      const doughSplit = this.dataItem["item_massa"]["item_massanome"].split(':');
      const name = doughSplit.length > 1 ? doughSplit[1] : doughSplit[0];
      itemEditing.dough = {
        id: this.dataItem["item_massa"]["item_massaid"],
        name,
        price: this.dataItem["item_massa"]["item_massapreco"]
      }
    
    }
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
  }

  setEdges() {
    itemEditing.edges = [];
    if (this.dataItem["item_borda"] && this.edges.length > 0) {
      for (const edge of this.dataItem["item_borda"]) {
        const edgeSplit = edge["item_bordanome"].split(':');
        const name = edgeSplit.length > 1 ? edgeSplit[1] : edgeSplit[0];
        itemEditing.edges.push({
          id: edge["item_bordaid"],
          name,
          price: edge["item_bordapreco"]
        });
      }
    
    }
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
  }

  setObservations() {
    itemEditing.observations = [];
    if (this.dataItem["item_observacoes"] && this.observations.length > 0) {
      for (const observation of this.dataItem["item_observacoes"]) {
        const name = observation["item_observacaonome"]
        itemEditing.observations.push({
          id: observation["item_observacaoid"],
          name,
          price: observation["item_observacaopreco"]
        });
      }
    
    }
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
  }

  updateIngredientsAddItemEditing(){
    for (let i = 0; i < itemEditing.ingredients.length; i++) {
      if (itemEditing.ingredients[i].ingredientsAdd.length == 0) continue;
      const getIngredients = this.getIngredients(itemEditing.ingredients[i].flavorId);

      for (let x = 0; x < itemEditing.ingredients[i].ingredientsAdd.length; x++) {
        const ingredientId = itemEditing.ingredients[i].ingredientsAdd[x].id;

        const getIngredient = getIngredients.ingredientsAdd.find(x => x.id == ingredientId);
        if (!getIngredient) continue;
        itemEditing.ingredients[i].ingredientsAdd[x].price = getIngredient.price;
      }
    }

    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
  }

  setIngredients() {
    itemEditing.ingredients = [];
    if (this.dataItem["sabores"].length > 0) {
      for (const flavor of this.dataItem["sabores"]) {
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
    sessionStorage.setItem('itemEditingED', JSON.stringify(itemEditing));
  }

  getIngredients(flavorId){
    const data = {
      ingredients: [],
      ingredientsAdd: [],
    }
    const flavor = this.flavors.find(x => x['sabor_id'] == flavorId);
    if (!flavor) return data;
    
    if (flavor["sabor_ingredientes"]) {
      for (const ingredient of flavor["sabor_ingredientes"]) {
        data.ingredients.push({
          id: ingredient["sabor_ingrediente_codingrediente"],
          name: ingredient["sabor_ingrediente_nomeingrediente"],
        })
      }
    }

    const typeCharge = this.allowedOptions ? this.allowedOptions["options"]["INGREDIENTE"]["COBRAR"] : null;

    if (typeCharge != "NP") {
      const sessionId = this.dataItem["item_sessaoid"];
      const sizeId = this.dataItem["item_tamanhoid"];
      const typeCalculation = getDataItem("typeCalculationIngredientsPerSlice");
      for (const ingredient of listIngredients) {
        if (ingredient["ingrediente_opcional"] == "N" || ingredient["ingrediente_sessaoid"] != sessionId) continue;
  
        let price = ingredient.ingrediente_preco ?? 0;
        price = typeCharge == "N" ? 0 : price;
        if (typeCharge == "S" || typeCharge === null) {
          if (Object.hasOwn(ingredient, "ingredientes_precotamanho") && ingredient["ingredientes_precotamanho"] === null) continue;

          if (typeCharge !== null && ingredient["ingredientes_precotamanho"]) {
            price = ingredient["ingredientes_precotamanho"].find(x => x["ingrediente_precotamannho_tamanhoid"] == sizeId);
            if (!price) continue;

            price = price ? price["ingrediente_precotamannho_preco"] : 0;
          }

          if (typeCalculation == "MEDIA") price = price / this.dataItem["sabores"].length;
        }

        data.ingredientsAdd.push({
          id: ingredient["ingrediente_id"],
          name: ingredient["ingrediente_nome"],
          price: parseFloat(price).toFixed(2)
        })
      }
    }

    return data;
  }

  renderSizes(){
    const currentSize = this.dataItem.item_tamanhoid;
    let options = "";
  
    for (let i = 0; i < this.sizes.length; i++) {
      const size = this.sizes[i];
      const id = size['tamanho_id'];
      const name = size['tamanho_nome'];
      const selected = id == currentSize ? "selected" : "";
      let descriptionText = "";
      if (size['tamanho_descricao']) {
        descriptionText = ` - ${size['tamanho_descricao']}`;
      }
      options += `<option value="${id}" ${selected}>${name} ${descriptionText}</option>`;
    }

    return options;
  }

  getQuantityFlavorBySize(sizeId){
    for(let i = 0; i < this.sizes.length; i++){
      if(this.sizes[i].tamanho_id == sizeId){
        if (this.sizes[i]?.tamanho_qtdmaxsabores) {
          return Array.isArray(this.sizes[i].tamanho_qtdmaxsabores) ? this.sizes[i].tamanho_qtdmaxsabores : JSON.parse(this.sizes[i].tamanho_qtdmaxsabores);
        }
        return Array.isArray(this.sizes[i].tamanho_qtdsabormaxima) ? this.sizes[i].tamanho_qtdsabormaxima : JSON.parse(this.sizes[i].tamanho_qtdsabormaxima);
      }
    }
    return [1];
  }

  getFlavorById(flavorId){
    return this.flavors.find(x => x["sabor_id"] == flavorId);
  }

  renderItemExtraInfo() {
    if ($(`.${this.instanceHash} #obs_item`).length == 0) return;

    if (this.extraInfoCurrent.length) {
      $(`.${this.instanceHash} #obs_item`).val(this.extraInfoCurrent);
      return;
    }

    if (
      this.dataItemCurrent.data_obs != undefined &&
      this.dataItemCurrent.data_obs != null &&
      this.dataItemCurrent.data_obs.length > 0
    ) {
      $(`.${this.instanceHash} #obs_item`).val(this.dataItemCurrent.data_obs);
    }
  }
}
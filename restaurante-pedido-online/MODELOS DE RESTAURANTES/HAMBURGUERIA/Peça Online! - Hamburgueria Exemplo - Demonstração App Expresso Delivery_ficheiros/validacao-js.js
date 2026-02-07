
$(document).ready(function () {
	
	var valueck = getCookie("promocoesrejeitadas");
	console.log(valueck);
	if(valueck != null){
		promocoesRejeitadas = getCookie("promocoesrejeitadas").split("and");
		promocoesRejeitadas = cleanArray(promocoesRejeitadas);
		if(promocoesRejeitadas.length>0){
			var ywydvg = promocoesRejeitadas.join("and");
			setCookie("promocoesrejeitadas", ywydvg);
		}
	}
    
    /* Inteiro */
    $(document).on("keypress",".inteiro",function(e){
        mascara(this, formatInteiro);
    });    
    $(document).on("keydown",".inteiro",function(e){
        mascara(this, formatInteiro);
    });
    $(document).on("keyup",".inteiro",function(e){
        mascara(this, formatInteiro);
    });
    
    /* decimalfixo */
    $(document).on("focus",".decimalfixo",function(e){
        var num = $(this).val();
        if (eval(num) === 0 || $(this).val() === "")
            $(this).val("0.00");
        $(this).select();
    }); 
    $(document).on("blur",".decimalfixo",function(e){
        var num = $(this).val();
        if (eval(num) === 0 || $(this).val() === "")
            $(this).val("0.00");
    }); 
    $(document).on("keypress",".decimalfixo",function(e){
        mascara(this, formatDecimalFixo);
    });    
    $(document).on("keydown",".decimalfixo",function(e){
        mascara(this, formatDecimalFixo);
    });
    $(document).on("keyup",".decimalfixo",function(e){
        mascara(this, formatDecimalFixo);
    });
    
    // hr completa
    $(document).on("keypress",".hrcompleta",function(e){
        mascara(this, mtempo);
    });
    $(document).on("keydown",".hrcompleta",function(e){
        mascara(this, mtempo);
    });
    $(document).on("keyup",".hrcompleta",function(e){
        mascara(this, mtempo);
    });
    $(document).on("blur",".hrcompleta",function(e){
        var vl = validahr($(this).val());
    });
    
    
    // data dmy
    $(document).on("keypress",".datadmy",function(e){
        mascara(this, mdata);
    });
    $(document).on("keydown",".datadmy",function(e){
        mascara(this, mdata);
    });
    $(document).on("keyup",".datadmy",function(e){
        mascara(this, mdata);
    });
    
    // datamdy
    $(document).on("keypress",".datamdy",function(e){
        mascara(this, mdata_mdy);
    });
    $(document).on("keydown",".datamdy",function(e){
        mascara(this, mdata_mdy);
    });
    $(document).on("keyup",".datamdy",function(e){
        mascara(this, mdata_mdy);
    });
    $(document).on("blur",".datamdy",function(e){
        mascara(this, mdata_mdy);
    });
    
    
    
    
    // cepvalid
    $(document).on("keypress",".cepvalid",function(e){
        mascara(this, mcep);
    });
    $(document).on("keydown",".cepvalid",function(e){
        mascara(this, mcep);
    });
    $(document).on("keyup",".cepvalid",function(e){
        mascara(this, mcep);
    });

    // telvalid
    $(document).on("keypress",".telvalid",function(e){
        mascara(this, mtel);
    });
    $(document).on("keydown",".telvalid",function(e){
        mascara(this, mtel);
    });
    $(document).on("keyup",".telvalid",function(e){
        mascara(this, mtel);
    });

    // EMAIL VALID
    $(document).on("blur",".emailvl",function(e){
        var valemail = $(this).val();
        if(valemail.length > 0){
            if (validarEmail(valemail) !== true) {
                var lblcampo = $(this).parent();
                lblcampo.addClass("errocampo");
            }
        }
    });
    
    // cpfvalid
    $(document).on("keypress",".cpfvalid",function(e){
        mascara(this, mcpf);
    });
    $(document).on("keydown",".cpfvalid",function(e){
        mascara(this, mcpf);
    });
    $(document).on("keyup",".cpfvalid",function(e){
        mascara(this, mcpf);
    });
    $(document).on("blur",".cpfvalid",function(e){
        var valor = $(this).val();
        if(valor.length > 0){
            if (!validarCPF(valor)) {
                //alert("CPF Inválido.");
                var lblcampo = $(this);//.parent();
                lblcampo.addClass("errocampo"); 
				lblcampo.parent().addClass("errocampo"); 
            }
        }
    });

    /////////////
    $(document).on("keyup",".cpfcnpjvalid",function(e){
        mascara(this, mcpfcnpj);
    });
    $(document).on("keydown",".cpfcnpjvalid",function(e){
        mascara(this, mcpfcnpj);
    });
    $(document).on("keypress",".cpfcnpjvalid",function(e){
        mascara(this, mcpfcnpj);
    });
    $(document).on("blur",".cpfcnpjvalid",function(e){
        mascara(this, mcpfcnpj);
    });
    /////////////
    $(document).on("keyup",".cnpjvalid",function(e){
        mascara(this, cnpj);
    });
    $(document).on("keydown",".cnpjvalid",function(e){
        mascara(this, cnpj);
    });
    $(document).on("keypress",".cnpjvalid",function(e){
        mascara(this, cnpj);
    });
    $(document).on("blur",".cnpjvalid",function(e){
        mascara(this, cnpj);
    });
    
    /*
     * js e css validação form
     */
    $(document).on("click",".errocampo",function(e){
        $(this).removeClass("errocampo");
    });

    $(document).on("focus",".compoform",function(e){
        $(this).removeClass("errocampo");
        $(this).parent().removeClass("errocampo");
    });
        
    /*
     * 
    label.form-cadastro { display: inline-block; width: 100%; padding: 5px 10px; font-size: 15px; border: #dddddd solid 1px; margin: 5px 0px 5px; background: #F9F9F9; }
    label.form-cadastro span { width: 100%; display: inline-block; padding: 3px 5px; color: #038F02; font-weight: 600; }
    label.form-cadastro input { width: 100%; display: inline-block; padding: 5px; border: none; background: #F9F9F9; letter-spacing: 2px; color: #555; }
    label.form-cadastro select { width: 100%; display: inline-block; padding: 5px; border: none; background: #F9F9F9; letter-spacing: 2px; color: #555; }
    .form-cadastro.errocampo{ border-color: rgb(231, 122, 122); background: rgb(255, 244, 244); }
    .form-cadastro.errocampo span{ color: rgb(189, 41, 41); }
    .form-cadastro.errocampo select, .form-cadastro.errocampo input{ background: #FFF4F4; }
    *
    */

});

function formatarParaReal(mixed) {
    var int = mixed.toFixed(2).toString().replace(/[^\d]+/g, '');
    var tmp = int + '';
    tmp = tmp.replace(/([0-9]{2})$/g, ",$1");
    //if (tmp.length > 6)
    //tmp = tmp.replace(/([0-9]{3}),([0-9]{2}$)/g, "$1,$2");
    tmp = tmp.replace(/\D/g, "");// Remove tudo o que não é dígito
    //tmp = tmp.replace(/(\d{2})(\d)/, "$1,$2");
    return tmp;
}
/*
 * 
 * @param {type} object
 * @returns {Boolean} Validação do formulario
 */
function validaform(elenform){
    
    var campos = elenform.find("[required='true']");
    var formok = true;
    var valsenha = "";
    $.each( campos, function( e ){
        //var nomecampo = $(this).data("nomecampo");
        //var tipocampo = $(this).data("tipocampo");

        var valorcampo = $(this).val();
        valorcampo = limparStr(valorcampo);

        var lblcampo = $(this).parent();

        if(valorcampo.length < 1){
            lblcampo.addClass("errocampo");
            formok = false;
            ////console.log(nomecampo);
        }else{            
            var validex = $(this).data("validex");
            if(validex !== undefined){
                if(validex === "nomecompleto"){
                    var nomes = valorcampo.split(" ");
                    if(nomes.length < 2){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "data"){
                    if(!validaData(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "cpf"){
                    if(!validarCPF(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "telefone"){
                    valorcampo = valorcampo.replace(/\D/g, "");
                    if(valorcampo.length !== 10 && valorcampo.length !== 11 ){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "email"){
                    if(!validarEmail(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "senha"){
                    valsenha = valorcampo;
                    if(valorcampo.length<6){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "conf-senha"){    
                    //console.log("senha: "+valsenha);
                    ////console.log(valorcampo);
                    if(valorcampo !== valsenha){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "cep"){    
                    valorcampo = valorcampo.replace(/\D/g, "");
                    if(valorcampo.length !== 8){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "numDec"){    
                    valorcampo = valorcampo.replace(/\D/g, "");
                    //valorcampo = ""+formatDecimalFixo(valorcampo)+"";
                    ////console.log(valorcampo);
                    if(valorcampo.length < 3){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "numInt"){    
                    valorcampo = ""+valorcampo.replace(/\D/g, "");
                    //valorcampo = ""+formatDecimalFixo(valorcampo)+"";
                    ////console.log(valorcampo);
                    if(valorcampo.length < 1){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }
            }
        }
    });
    
    var camposEX = elenform.find("[data-validex]");
    $.each( camposEX, function( e ){
        //var nomecampo = $(this).data("nomecampo");
        //var tipocampo = $(this).data("tipocampo");

        var valorcampo = $(this).val();
        valorcampo = limparStr(valorcampo);

        var lblcampo = $(this);//.parent();

        if(valorcampo.length > 0){
            
            var validex = $(this).data("validex");
            if(validex !== undefined){
                if(validex === "nomecompleto"){
                    var nomes = valorcampo.split(" ");
                    if(nomes.length < 2){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "data"){
                    if(!validaData(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "cpf"){
                    if(!validarCPF(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "telefone"){
                    valorcampo = valorcampo.replace(/\D/g, "");
                    if(valorcampo.length !== 10 && valorcampo.length !== 11 ){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "email"){
                    if(!validarEmail(valorcampo)){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "senha"){
                    valsenha = valorcampo;
                    if(valorcampo.length<6){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "conf-senha"){    
                    //console.log("senha: "+valsenha);
                    ////console.log(valorcampo);
                    if(valorcampo !== valsenha){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "cep"){    
                    valorcampo = valorcampo.replace(/\D/g, "");
                    if(valorcampo.length !== 8){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "numDec"){    
                    valorcampo = valorcampo.replace(/\D/g, "");
                    //valorcampo = ""+formatDecimalFixo(valorcampo)+"";
                    ////console.log(valorcampo);
                    if(valorcampo.length < 3){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }else if(validex === "numInt"){    
                    valorcampo = ""+valorcampo.replace(/\D/g, "");
                    //valorcampo = ""+formatDecimalFixo(valorcampo)+"";
                    ////console.log(valorcampo);
                    if(valorcampo.length < 1){
                        lblcampo.addClass("errocampo");
                        formok = false;
                    }
                }
            }
        }
    });
    
    return formok;
    
}


/* verifica se elemento de entrada é um array 
 */
function is_array(object) {
    if (object.constructor === Array)
        return true;
    else
        return false;
}

/*
 * Primeira letra maiúscla de cada palavra da string
 */
function capitalize(_string) {
    try{
    _string = _string.toLowerCase();
    return _string.replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); });
    }catch(e){
        //console.log("ERRO "+_string);
    }
};


function removeA(arr) {
    var what, a = arguments, L = a.length, ax;
    while (L > 1 && arr.length) {
        what = a[--L];
        while ((ax= arr.indexOf(what)) !== -1) {
            arr.splice(ax, 1);
        }
    }
    return arr;
}

function cleanArray(actual) {
  var newArray = new Array();
  for (var i = 0; i < actual.length; i++) {
    if (actual[i]) {
      newArray.push(actual[i]);
    }
  }
  return newArray;
}

function is_null(obj) {
    return obj === null;
}

function is_float(n) {
    return n === +n && n !== (n | 0);
}

function is_int(n) {
    return typeof (n) === "number" && Math.round(n) == n;
}

function is_numeric(obj) {
    return /^[0-9]+[\.,]{0,1}[0-9]*$/i.test(obj);
}

function is_string(obj) {
    return (typeof (obj) === 'string');
}

function in_array(needle, haystack) {
    for (var i in haystack) {
        if (haystack[i] == needle)
            return true;
    }
    return false;
}

function clone(obj) {
    if (obj === null || typeof (obj) !== 'object')
        return obj;
    var temp = new obj.constructor();
    for (var key in obj)
        temp[key] = clone(obj[key]);
    return temp;
}

// remove todos os espaços em branco que tiver na string
function trim(str) {
    return str.replace(/^\s+|\s+$/g, "");
}

function ltrim(str){
    return str.replace(/^\s+/,"");
}
function rtrim(str){
    return str.replace(/\s+$/,"");
}


function strip_tags(input, allowed) {
    allowed = (((allowed || '') + '').toLowerCase().match(/<[a-z][a-z0-9]*>/g) || []).join(''); // making sure the allowed arg is a string containing only tags in lowercase (<a><b><c>)
    var tags = /<\/?([a-z][a-z0-9]*)\b[^>]*>/gi,commentsAndPhpTags = /<!--[\s\S]*?-->|<\?(?:php)?[\s\S]*?\?>/gi;
    return input.replace(commentsAndPhpTags, '').replace(tags, function ($0, $1) {
            return allowed.indexOf('<' + $1.toLowerCase() + '>') > -1 ? $0 : '';
        });
}

function mascara(o, f) {
    v_obj = o;
    v_fun = f;
    setTimeout("execmascara()", 1);
}

function cnpj(v) {
    v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
    v = v.replace(/^(\d{2})(\d)/, "$1.$2"); // Coloca ponto entre o segundo e o
    v = v.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3"); // Coloca ponto entre o
    v = v.replace(/\.(\d{3})(\d)/, ".$1/$2"); // Coloca uma barra entre o
    v = v.replace(/(\d{4})(\d)/, "$1-$2"); // Coloca um hífen depois do bloco
    return v;
}
function execmascara() {
    v_obj.value = v_fun(v_obj.value);
}

function cartaocredito(v) {
    if(v!== null && v.length > 0){
    v = v.replace(/\D/g, "");
    var gu = v;
    v = v.replace(/(\d{4})(\d)/, "$1-$2");

    v = v.replace(/(\d{6})(\d)/, "$1-$2");
    if (gu.length > 14) {
        v = v.replace(/\D/g, "");
        v = v.replace(/(\d{4})(\d)/, "$1-$2");
        v = v.replace(/(\d{4})(\d)/, "$1-$2");
        v = v.replace(/(\d{4})(\d)/, "$1-$2");
    }
    }
    return v;
}

function mcpf(v) {
    if(v!== null && v.length > 0){
        v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
        v = v.replace(/(\d{3})(\d)/, "$1.$2"); // Coloca um ponto entre o terceiro
        // e o quarto dígitos
        v = v.replace(/(\d{3})(\d)/, "$1.$2"); // Coloca um ponto entre o terceiro
        // e o quarto dígitos
        v = v.replace(/(\d{3})(\d{1,2})$/, "$1-$2"); // Coloca um hífen entre o
        // terceiro e o quarto
        // dígitos
    }
    return v;
}

function mcpfcnpj(v) {
    if(v!== null && v.length > 0 && v.length < 15){
        v = mcpf(v);
    }else if(v!== null && v.length > 14){
        v = cnpj(v);
    }
    return v;
}

function mtel(v) {
    if(v!== null && v.length > 0){
    v = v.replace(/\D/g, "");// Remove tudo o que não é dígito
    if (v.length <= 10) {
        v = v.replace(/^(\d\d)(\d)/g, "($1) $2"); // Coloca parênteses em
        // volta dos dois primeiros
        // dígitos
        v = v.replace(/(\d{4})(\d)/, "$1-$2"); // Coloca hífen entre o quarto e
        // o quinto dígitos
    } else {
        v = v.replace(/^(\d{2})(\d{1})(\d{4})(\d{4})$/, "($1) $2-$3-$4");
    }
    }
    return v;
}

function formatDecimal(v) {
    if(v!== null && v.length > 0){
        v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
        v = v.replace(/(\d{3})(\d)/, "$1,$2"); // Coloca hífen entre o 4 e o 3
    }
    return v;
}

function checkValReal(v) {
    try{
        if(v!== null && v.length > 0){
        v = v.replace(/\D/g, "");
        v = v.replace(/^(\d{1,})(\d{2})$/, "$1.$2");
        if(v.length === 0){v = 0;}
        }
    }catch(erjs){ v="0.00";}
    return v;
}

function formatDecimalFixo(v) {
    if(v!== null && v.length > 0){
    var integer = v.split(',')[0];
    v = v.replace(/\D/g, "");
    v = v.replace(/^[0]+/, "");
    if (v.length <= 2 || !integer) {
            if(v.length === 1)
                    v = '0,0' + v;
            if(v.length === 2)
                    v = '0,' + v;
    } else {
            v = v.replace(/\D/g, "");
            v = v.replace(/^(\d{1,})(\d{2})$/, "$1,$2");
    }
    if (v == 0) {
            v = "0,00";
    }
    v = v.replace(",", ".");
    }
    return v;
}

function mdata(v) {
    if(v!== null && v.length > 0){
        v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
        v = v.replace(/(\d{2})(\d)/, "$1/$2");
        v = v.replace(/(\d{2})(\d)/, "$1/$2");

        v = v.replace(/(\d{2})(\d{2})$/, "$1$2");
    }
    return v;
}

function mdata_mdy(v) {
    if(v!== null && v.length > 0){
        v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
        v = v.replace(/(\d{2})(\d)/, "$1/$2");
        v = v.replace(/(\d{2})(\d)/, "$1/$2");

        v = v.replace(/(\d{2})(\d{2})$/, "$1$2");
    }
    return v;
}

function formatInteiro(v) {
    if(v!== null && v.length > 0){
        v = v.replace(/\D/g, "");
    }
    return v;
}

function mtempo(v) {
    if(v!== null && v.length > 0){
    v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
    v = v.replace(/(\d{2})(\d)/, "$1:$2");
    v = v.replace(/(\d{2})(\d)/, "$1:$2");
    v = v.replace(/(\d{2})(\d{2})$/, "$1$2");
    }
    return v;
}

function mcep(v) {
    if(v!== null && v.length > 0){
    v = v.replace(/\D/g, ""); // Remove tudo o que não é dígito
    v = v.replace(/^(\d{5})(\d)/, "$1-$2"); // Esse é tão fácil que não merece
    }
    return v;
}

function invertData(data){
    var datas = data.split("-");
    return datas[2]+"/"+datas[1]+"/"+datas[0];
}

function validaData(data) {//dd/mm/aaaa
    //data = invertData(data);
    
    try {
        if (data.length !== 10)
            throw "Data inválida";
        var day = data.substring(0, 2);
        if (parseInt(day))
            day = parseInt(day);
        else
            throw "Dia Data inválido";
        var month = data.substring(3, 5);
        if (parseInt(month))
            month = parseInt(month);
        else
            throw "Mês Data inválido";
        var year = data.substring(6, 10);
        if (parseInt(year))
            year = parseInt(year);
        else
            throw "Ano Data inválido";
        ////console.log(day + " " + month + " " + year);        
        var anoatual = 2016;
        if ((month > 0 && month <= 12) && (year > 1900 && year < anoatual) && (day > 0 && day <= 31)) {
            if ((month === 01) || (month === 03) || (month === 05) || (month === 07) || (month === 08) || (month === 10) || (month === 12)) {//mes com 31 dias
                if ((day < 01) || (day > 31)) {
                    throw "Data invalida";
                }
            } else {
                if ((month === 04) || (month === 06) || (month === 09) || (month === 11)) {//mes com 30 dias
                    if ((day < 01) || (day > 30)) {
                        throw "Data invalida";
                    }
                } else {
                    if ((month === 2)) {//February and leap year
                        if ((year % 4 === 0) && ((year % 100 !== 0) || (year % 400 === 0))) {
                            if ((day < 01) || (day > 29)) {
                                throw "Data invalida";
                            }
                        } else {
                            if ((day < 01) || (day > 28)) {
                                throw "Data invalida";
                            }
                        }
                    }
                }
            }
        } else {
            throw "Condições Data invalida";
        }
        return true;
    } catch (err) {
        //return err;
        //console.log(err);
        return false;
    }
}
/*
function validaHRexreg(hr){
    
    var matchhora = new RegExp(/^([0-1][0-9]|2[0-3]):[0-5][0-9]$/gi);
    
}
*/
function validahr(hr) {
    try {
        if(hr.length === 4 || hr.length === 7){
            hr = "0"+hr;
        }
        
        var conthr = hr.length;
        if (conthr === 8 || conthr === 5) {
            var hora = hr.split(":");
            
            if( (conthr === 5 && hora.length === 2) || (conthr === 8 && hora.length === 3) ){
            
                var h = eval(hora[0]);
                var m = eval(hora[1]);
                if (!is_int(h)) {
                    throw "Hora invalida";
                }
                if (!is_int(m)) {
                    throw "Hora invalida";
                }
                if (conthr === 8 && hora.length === 3) {
                    var s = eval(hora[2]);
                    if (!is_int(s)) {
                        throw "Hora invalida.";
                    }
                    if (s > 59) {
                        throw "Hora invalida, segundos acima de 59.";
                    }
                }
                if (h > 23 || m > 59) {
                    throw "Hora invalida, hora ou minito acima do normal.";
                }
            }else{
                throw "Hora invalida.";
            }
        } else {
            throw "Hora invalida";
        }
        return true;
    } catch (err) {
        //return err;
        //console.log(err);
        return false;
    }
}

function validarCNPJ(cnpj) {

    cnpj = cnpj.replace(/[^\d]+/g, '');
    cnpj = '' + cnpj + '';
    if (cnpj === '')
        return false;

    if (cnpj.length !== 14)
        return false;

    // Elimina CNPJs invalidos conhecidos
    if (cnpj === "00000000000000" || cnpj === "11111111111111"
            || cnpj === "22222222222222" || cnpj === "33333333333333"
            || cnpj === "44444444444444" || cnpj === "55555555555555"
            || cnpj === "66666666666666" || cnpj === "77777777777777"
            || cnpj === "88888888888888" || cnpj === "99999999999999")
        return false;

    // Valida DVs
    var tamanho = cnpj.length - 2;
    var numeros = cnpj.substring(0, tamanho);
    var digitos = cnpj.substring(tamanho);
    var soma = 0;
    var pos = tamanho - 7;
    for (var i = tamanho; i >= 1; i--) {
        soma += numeros.charAt(tamanho - i) * pos--;
        if (pos < 2)
            pos = 9;
    }
    var resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
    if (resultado != digitos.charAt(0))
        return false;

    tamanho = tamanho + 1;
    numeros = cnpj.substring(0, tamanho);
    soma = 0;
    pos = tamanho - 7;
    for (i = tamanho; i >= 1; i--) {
        soma += numeros.charAt(tamanho - i) * pos--;
        if (pos < 2)
            pos = 9;
    }
    resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
    if (resultado != digitos.charAt(1))
        return false;

    return true;
}

function validarEmail(email) {
    var filter = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$/i;
    if (!filter.test(email)) {
        return false;
    }
    return true;
}

function validarCPF(cpf) {
    cpf = cpf.replace(/[^\d]+/g, '');
    cpf = '' + cpf + '';
    if (cpf === '')
        return false;
    // Elimina CPFs invalidos conhecidos
    if (cpf.length !== 11 || cpf === "00000000000" || cpf === "11111111111"
            || cpf === "22222222222" || cpf === "33333333333"
            || cpf === "44444444444" || cpf === "55555555555"
            || cpf === "66666666666" || cpf === "77777777777"
            || cpf === "88888888888" || cpf === "99999999999")
        return false;
    // Valida 1o digito
    var add = 0;
    for (var i = 0; i < 9; i++)
        add += parseInt(cpf.charAt(i)) * (10 - i);
    var rev = 11 - (add % 11);

    if (rev === 10 || rev === 11)
        rev = 0;
    if (rev != parseInt(cpf.charAt(9)))
        return false;
    // Valida 2o digito
    add = 0;
    for (i = 0; i < 10; i++)
        add += parseInt(cpf.charAt(i)) * (11 - i);
    rev = 11 - (add % 11);
    if (rev === 10 || rev === 11)
        rev = 0;
    if (rev != parseInt(cpf.charAt(10)))
        return false;
    return true;
}

function limparStr(str){
    str = strip_tags(str, "");
    str = ltrim(str);
    str = rtrim(str);
    str = str.replace(/\s{2,}/g, ' ');//elimina espaços duplicados
    /*
        \s - qualquer espaço em branco
        {2,} - em quantidade de dois ou mais
        g - apanhar todas as ocorrências, não só a primeira
        depois o replace faz a subsituição desses grupos de espaços pelo que fôr passado no segundo parâmetro. Neste caso um espaço simples , ' ');
     */
    return str;
}

function sleep(milliseconds) {
    var start = new Date().getTime();
    for (var i = 0; i < 1e7; i++) {
      if ((new Date().getTime() - start) > milliseconds){
        break;
      }
    }
}


function mt_rand(min, max) {
    // *     example 1: mt_rand(1, 1);
    // *     returns 1: 1
    var argc = arguments.length;
    if (argc === 0) {
        min = 0;
        max = 2147483647;
    } else if (argc === 1) {
        throw new Error('Warning: mt_rand() expects exactly 2 parameters, 1 given');
    } else {
        min = parseInt(min, 10);
        max = parseInt(max, 10);
    }
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function gerarValor(tamanho, maiusculas, numeros, simbolos) {
    var lmin = 'abcdefghijklmnopqrstuvwxyz';
    var lmai = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    var num = '1234567890';
    var simb = '!@#$%*-';
    var retorno = '';
    var caracteres = '';

    caracteres += lmin;
    if (maiusculas != undefined)
        caracteres += lmai;
    if (numeros != undefined)
        caracteres += num;
    if (simbolos != undefined)
        caracteres += simb;

    var len = caracteres.length;
    for (var n = 1; n <= tamanho; n++) {
        var rand = mt_rand(1, len);
        retorno += caracteres[rand - 1];
    }
    return retorno;
}

function parseReal(valor){
    try{
        valor = parseFloat(valor);
        return (valor).formatMoney(2,",",".");
    }catch(e){
        return (0.00).formatMoney(2,",",".");
    }
}

/*
 * Get Intersection
 * getIntersection([1,2], [1,3]) // 1
 * getIntersection.apply(this, [[a,b], [c,b], [d,b]]) // b
 */
getIntersection: function getIntersection() {
  var list = arguments;
  var result = [];
  for (var i =0; i < list.length; i++) {
    if (i === 0) { result = list[i]; }
 
    var tempIntersection = result.filter(function(n) {
      return list[i].indexOf(n) != -1;
    });
 
    result = [];
    tempIntersection.map(function(y){ result.push(y)});
  }
 
  return result;
};

function setCookie(name, value, duration) {
	if(duration == undefined){
		var date = new Date();
		//date.setDate(date.getDate() + 1);
		date.setDate(date.getHours() + 12);		
		duration = date;
		//duration = date.toGMTString();
	}
	
	var cookie = name + "=" + escape(value) +
	((duration) ? ";path=/; duration=" + duration.toGMTString() : "");

	document.cookie = cookie;
}
function getCookie(name) {
    var cookies = document.cookie;
    var prefix = name + "=";
    var begin = cookies.indexOf("; " + prefix);
	
    if (begin == -1) {
 
        begin = cookies.indexOf(prefix);
         
        if (begin != 0) {
            return null;
        }
 
    } else {
        begin += 2;
    }
 
    var end = cookies.indexOf(";", begin);
     
    if (end == -1) {
        end = cookies.length;                        
    }
 
    return unescape(cookies.substring(begin + prefix.length, end));
}
function deleteCookie(name) {
   if (getCookie(name)) {
	  document.cookie = name + "=" +
	  "; expires=Thu, 01-Jan-70 00:00:01 GMT";
   }
}

function validarCNPJCPF(vl){
    if(validarCPF(vl)){
        return true;
    }else if(validarCNPJ(vl)){
        return true;
    }
    return false;
}

/* Formatar numero para moeda */
Number.prototype.formatMoney = function(c, d, t){
var n = this, c = isNaN(c = Math.abs(c)) ? 2 : c, d = d == undefined ? "," : d, t = t == undefined ? "." : t, s = n < 0 ? "-" : "", i = parseInt(n = Math.abs(+n || 0).toFixed(c)) + "", j = (j = i.length) > 3 ? j % 3 : 0;
   return s + (j ? i.substr(0, j) + t : "") + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + t) + (c ? d + Math.abs(n - i).toFixed(c).slice(2) : "");
};
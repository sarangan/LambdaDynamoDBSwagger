var AWS = require('aws-sdk');
const BC_TABLE = "dev_bc_videos";

//fatten S N M L from object
let flatten = (o) => {

  let descriptors = ['L', 'M', 'N', 'S'];

  // flattens single property objects that have descriptors
  for (let d of descriptors) {
    if (o.hasOwnProperty(d)) {
      return o[d];
    }
  }

  Object.keys(o).forEach((k) => {

    for (let d of descriptors) {
      if (o[k].hasOwnProperty(d)) {
        o[k] = o[k][d];
      }
    }
    if (Array.isArray(o[k])) {
      o[k] = o[k].map(e => flatten(e))
    } else if (typeof o[k] === 'object') {
      o[k] = flatten(o[k])
    }
  });

  return o;
}

//check if has image and name
let checkCanAdd = (item) =>{
  // add the sph copyright no
  if(item.hasOwnProperty('images') && item.hasOwnProperty('name') && item.hasOwnProperty('custom_fields') ){
    if( item['images'].hasOwnProperty('poster') && item.images.poster.length > 0 && item.name.length > 0 && item.custom_fields.hasOwnProperty('sphcopyright') ){
      if(item.custom_fields['sphcopyright'].trim().toLowerCase() != "no" ){
        return true;
      }
    }
  }

  return false;

}

// get previous date
let getInPrevDate = (mon = 1) =>{

  let d = new Date();
  d.setMonth(d.getMonth() - mon);
  let day = d.getDate();
  let monthIndex = d.getMonth();
  let year = d.getFullYear();

  return `${year}-${monthIndex+1}-${day}`;
}

//get top viewed in category used for trending
let getTopCategoryData = async (category) =>{

  let params = {
    TableName: BC_TABLE,
    ExpressionAttributeValues :{
      ':category': {
          'S': category,
      },
      ':video_view': {
          'N': '0',
      }
    },
    KeyConditionExpression: 'li_category = :category AND video_view >= :video_view',
    IndexName: 'li_category-video_view-index',
    ScanIndexForward: false,
    Limit: 1
  };

  const data = await ddb.query(params).promise();

  return data;

}

//get lasted in category used for trending
let getLatestCategoryData = async (category, months = 3, limit = 1) =>{

  let params = {
    TableName: BC_TABLE,
    ExpressionAttributeValues :{
      ':category': {
          'S': category,
      },
      ':publish_date':{
        'S' : getInPrevDate(months)
      }
    },
    KeyConditionExpression: 'li_category = :category and published_at > :publish_date',
    IndexName: 'li_category-published_at-index',
    ScanIndexForward: false,
    Limit: limit
  };

  const data = await ddb.query(params).promise();

  return data;

}


exports.apiHandler = async (event, context) => {

  const category_array = ['beauty', 'entertainment', 'fashion', 'food', 'lifestyle', 'tech', 'wellness' ];

  ddb = new AWS.DynamoDB();

  if ('video_id' in event && event.video_id){

    const video_id = event.video_id;

    var params = {
      TableName: BC_TABLE,
      ExpressionAttributeValues :{
        ':vid': {
            'N': video_id,
        },
      },
      KeyConditionExpression: 'id = :vid',
      //ProjectionExpression: 'published_at'
    };

    try {
      const data = await ddb.query(params).promise();
      let formated_data = {};

      if(data && data.hasOwnProperty('Items')){

        if(data['Items'].length > 0 ){
          formated_data = flatten(data['Items'][0]);
        }

      }

      return { statusCode: 200, body: formated_data};
    } catch (error) {
      return {
        statusCode: 400,
        error: `Could not fetch: ${error.stack}`
      };
    }

  }


  //get categories
  if('category' in event && event.category){

      const category = event.category;

      let limit = 0;

      if('limit' in event && event.limit){
        limit = parseInt(event.limit);
      }

      let exclusiveKey = null;

      if('last_key' in event && event.last_key){ // build last key

        if(event.last_key){
          let last_arr = event.last_key.split(';');
          if(last_arr && last_arr.length > 0){
            let last_vid = last_arr[0];
            let last_published_key = last_arr[1];

            if(last_vid && last_published_key){
              exclusiveKey = {
                'id': {'N': last_vid },
                'li_category': {'S': category},
                'published_at': {'S': last_published_key}
              };
            }

          }
        }
      }


      var params = {
        TableName: BC_TABLE,
        ExpressionAttributeValues :{
          ':category': {
              'S': category,
          }
        },
        KeyConditionExpression: 'li_category = :category',
        IndexName: 'li_category-published_at-index',
        ScanIndexForward: false
      };

      if(exclusiveKey){
        params['ExclusiveStartKey'] = exclusiveKey;
      }

      if(limit){
        params['Limit'] = limit;
      }

      try {

          if('islatest' in event && event.islatest){ // for home page


            let formated_data_category = {};

            //------
            for (let temp_category of category_array) {
                let formated_data = [];

                let cat_latest_data = await getLatestCategoryData(temp_category, 3, limit);

                if(cat_latest_data && cat_latest_data.hasOwnProperty('Items')){

                  for(let i = 0,l = cat_latest_data['Items'].length; i < l; i++){

                    if(cat_latest_data['Items'][i].hasOwnProperty('id')){
                      let temp_data = flatten(cat_latest_data['Items'][i]);
                      if(checkCanAdd(temp_data)){
                        formated_data.push(temp_data);
                      }
                    }

                  }
                  //add to main obj
                  formated_data_category[temp_category] = formated_data;

                }
           }

           return { statusCode: 200, body: formated_data_category };


          }
          else{

              const data = await ddb.query(params).promise();
              let formated_data = [];
              let last_key = '';

              if(data){

                if(data.hasOwnProperty('Items')){
                  let items = data['Items'];

                  for(let i = 0,l = items.length; i < l; i++){

                    let temp_data = flatten(items[i]);
                    //stupid check
                    if(checkCanAdd(temp_data)){
                      formated_data.push(temp_data);
                    }

                  }
                }

                if(data.hasOwnProperty('LastEvaluatedKey')){
                  last_key = data['LastEvaluatedKey'];
                }

              }

              return { statusCode: 200, body: formated_data, LastEvaluatedKey: last_key };

          }


      }
      catch(error){
          return {
            statusCode: 400,
            error: `Could not fetch: ${error.stack}`
          };
      }

  }

  if('playlist' in event && event.playlist){ // get playlist Featured videos

      const playlist = event.playlist;

      let limit = 20;
      var params = {};
      var data = null;

      if('limit' in event && event.limit){
        limit = parseInt(event.limit);
      }

      try {

        if(playlist != 'trending'){

          params = {
            TableName: BC_TABLE,
            ExpressionAttributeValues :{
              ':category': {
                  'S': playlist,
              },
              ':video_view': {
                  'N': '0',
              }
            },
            KeyConditionExpression: 'li_category = :category AND video_view >= :video_view',
            IndexName: 'li_category-video_view-index',
            ScanIndexForward: false,
          };

          if(limit){
            params['Limit'] = limit;
          }


            data = await ddb.query(params).promise();
            let formated_data = [];

            if(data && data.hasOwnProperty('Items')){

              let items = data['Items'];

              for(let i = 0,l = items.length; i < l; i++){

                let temp_data = flatten(items[i]);
                //stupid check
                if(checkCanAdd(temp_data)){ // check name image exists
                  formated_data.push(temp_data);
                }

              }

            }

            return { statusCode: 200, body: formated_data };


        }
        else{

          //trending videos

          let formated_data = [];
          let video_ids = new Set();


          //--------- get users perference ------

          if('user_category' in event && event.user_category){
            let usercategory = event.user_category;

            params = {
              TableName: BC_TABLE,
              ExpressionAttributeValues :{
                ':category': {
                    'S': usercategory,
                }
              },
              KeyConditionExpression: 'li_category = :category',
              IndexName: 'li_category-published_at-index',
              ScanIndexForward: false,
              Limit: 3
            };

            data = await ddb.query(params).promise();

            if(data && data.hasOwnProperty('Items')){

              for(let i = 0,l = data['Items'].length; i < l; i++){

                if(data['Items'][i].hasOwnProperty('id')){
                  if(!video_ids.has(data['Items'][i]['id']['N'])){
                    let temp_data = flatten(data['Items'][i]);
                    if(checkCanAdd(temp_data)){
                      formated_data.push(temp_data);
                      video_ids.add(temp_data.id);
                    }
                  }
                }

              }

            }


          }


          //------------- get tending -----

          for (let temp_category of category_array) {
             let cat_data = await getTopCategoryData(temp_category);
             if(cat_data && cat_data.hasOwnProperty('Items')){

               for(let i = 0,l = cat_data['Items'].length; i < l; i++){

                 if(cat_data['Items'][i].hasOwnProperty('id')){
                   if(!video_ids.has(cat_data['Items'][i]['id']['N'])){
                     let temp_data = flatten(cat_data['Items'][i]);
                     if(checkCanAdd(temp_data)){
                       formated_data.push(temp_data);
                       video_ids.add(temp_data.id);
                     }
                   }
                 }

               }

             }

          }

          //------------- get latest -----

          /* reduce download size
            for (let temp_category of category_array) {

                let cat_latest_data = await getLatestCategoryData(temp_category);

                if(cat_latest_data && cat_latest_data.hasOwnProperty('Items')){

                  for(let i = 0,l = cat_latest_data['Items'].length; i < l; i++){

                    if(cat_latest_data['Items'][i].hasOwnProperty('id')){
                      if(!video_ids.has(cat_latest_data['Items'][i]['id']['N'])){
                        let temp_data = flatten(cat_latest_data['Items'][i]);
                        if(checkCanAdd(temp_data)){
                          formated_data.push(temp_data);
                          video_ids.add(temp_data.id);
                        }
                      }
                    }

                  }

                }
          }
          */




          return { statusCode: 200, body: formated_data };


        }//end else



      }
      catch (error) {
        return {
          statusCode: 400,
          error: `Could not fetch: ${error.stack}`
        };
      }


    }

  if('search_query' in event && event.search_query){ // search by name and description

        const search_query = event.search_query;

        let exclusiveKey = null;

        if('last_key' in event && event.last_key){

          if(event.last_key){
            let last_arr = event.last_key.split(';');
            if(last_arr && last_arr.length > 0){
              let last_vid = last_arr[0];
              let last_published_key = last_arr[1];

              if(last_vid && last_published_key){
                exclusiveKey = {
                  'id': {'N': last_vid },
                  'published_at': {'S': last_published_key}
                };
              }

            }
          }
        }

        let params = {
             ExpressionAttributeValues: {
              ":search_query": {
                'S': search_query
               }
             },
             ExpressionAttributeNames: {
                "#name" : "name",
                "#description" : "description",
                "#tags" : "tags",
                "#long_description": "long_description"
             },
             FilterExpression: "contains (#name, :search_query) or contains (#description, :search_query) or contains (#tags, :search_query) or contains (#long_description, :search_query)",
             TableName: BC_TABLE
        };


        // for tag search
        if(search_query.indexOf('tags:') !== -1){

          params = {
               ExpressionAttributeValues: {
                ":tag_search": {
                  'S': search_query.replace('tags:', '')
                 }
               },
               FilterExpression: "contains (tags, :tag_search)",
               TableName: BC_TABLE
          };

        }


        if(exclusiveKey){
          params['ExclusiveStartKey'] = exclusiveKey;
        }


        try{

            const data = await ddb.scan(params).promise();
            let formated_data = [];
            let last_key = '';
            let video_ids = new Set();

            if(data){

              if(data.hasOwnProperty('Items')){

                if(data['Items']){

                  for(let i =0, l = data['Items'].length; i < l ; i++){
                    if(data['Items'][i].hasOwnProperty('id')){
                      if(!video_ids.has(data['Items'][i]['id']['N'])){
                        let temp_data = flatten(data['Items'][i]);
                        if(checkCanAdd(temp_data)){
                          formated_data.push(temp_data);
                          video_ids.add(temp_data.id);
                        }
                      }
                    }
                  }
                }

              }

              if(data.hasOwnProperty('LastEvaluatedKey')){
                last_key = data['LastEvaluatedKey'];
              }

            }

            return { statusCode: 200, body: formated_data, LastEvaluatedKey: last_key };
        }
        catch(error){
            return {
              statusCode: 400,
              error: `Could not fetch: ${error.stack}`
            };
        }


      }


};

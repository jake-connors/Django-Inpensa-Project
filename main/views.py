from django.shortcuts import render, redirect
from django.db import models
from django.http import HttpResponse
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .forms import SetForm, ModelForm
from .models import dataset, data, model, prediction
from django.db.models import Q
import pandas as pd
from sklearn import preprocessing
import tensorflow as tf
from json import dumps
from django.views.generic import View
from django.http import JsonResponse, Http404
from sklearn.model_selection import train_test_split
import os
import json.encoder
from django.views.decorators.csrf import csrf_exempt
# Create your views here.

def login(request):
    if request.method == 'POST':
        username = request.POST['uname']
        password = request.POST['psw']

        user = auth.authenticate(username = username, password =password)
        if user is not None:
            auth.login(request, user)
            return redirect('dash')
        
        else:
            messages.info(request,'invalid username or password')
            return redirect('/')
        
    else:
        if request.user.is_authenticated:
            return redirect('dash')
        else:
            return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        first_name = request.POST['fname']
        last_name = request.POST['lname']
        email = request.POST['email']
        user_name = request.POST['uname']
        password1 = request.POST['psw']
        if User.objects.filter(username = user_name).exists():
            messages.info(request,'Username taken')
            return redirect('register')
        elif User.objects.filter(email=email).exists():
            messages.info(request,'Email taken')
            return redirect('register')
        else:
            user = User.objects.create_user(username = user_name, password = password1, email = email, first_name= first_name, last_name = last_name)
            
            user.save()
            messages.info(request,'Account registered successfully')
            return redirect('login')
    else:
        return render(request, 'register.html')

def forgot(request):
    return render(request, 'forgot.html')

def dash(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        sets2 =  model.objects.all().filter(user = request.user).values()
        print(sets)
        return render(request, 'dashboard.html',{
            'sets': sets,
            'sets2': sets2
        })
    else:
        return redirect('login')

def logout(request):
    auth.logout(request)
    messages.info(request,'You have successfully logged out')
    return redirect('/')

'''
def upload(request):
    context = {}
    if request.method =='POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
    return render(request, 'upload.html', context)


'''



##upload page that lets the user upload a new file



def upload_db(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            f = request.FILES['Project Data'].temporary_file_path()
            try:
                df = pd.read_excel(f)
            except Exception:
                df = pd.read_csv(f)
            form = SetForm(request.POST)
            if form.is_valid():
                df = df.reset_index().groupby("ID", as_index=False).max()
                df['accepted'] = 0
                instance = dataset(user = request.user, name = request.POST['name'], budget = request.POST['budget'])
                instance.save()
                df_records = df.to_dict('records')
                
                model_instances = [data(
                    name =record['ID'],
                    TCO =record['TCO'],
                    TVO =record['TVO'],
                    NET =record['NET'],
                    PP =record['PP'],
                    ROI =record['ROI'],
                    CapEx =record['CapEx'],
                    OneTime =record['OneTime'],
                    OnGoing =record['OnGoing'],
                    Revenue =record['Revenue'],
                    Saving =record['Saving'],
                    Avoid =record['Avoid'],
                    CostGrade =record['Cost Grade'],
                    ValueScore =record['Value Score'],
                    RiskScore =record['Risk Score'],
                    BlendedScore =record['Blended Score'],
                    CalcPriority =record['Calc Priority'],
                    OverridedPriority =record['Overrided Priority'],
                    dsid = instance,
                    accepted = record['accepted']
                    
                ) for record in df_records]
                data.objects.bulk_create(model_instances)

                count = data.objects.filter(dsid = instance).count()
                if (count != 0):
                    instance.size = count
                    instance.save()
                else:
                    instance.delete()


            
            return redirect('dash')
                

        else:
            form = SetForm()
            return render(request, 'upload_db.html',{'form': form})
    else:
        return redirect('login')


def test(request):
    return render(request, 'test.html')



##shows the list of files uploaded by that user

def set_list(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        return render(request, 'set_list.html',{
            'sets': sets
        })
    else:
        return redirect('login')

def view(request):
    if request.user.is_authenticated:
        if request.method=="POST":



            return render(request, 'view_dataset.html')
        else:
            sets = data.objects.all().filter(dsid = request.GET['dataset']).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['Overrided Priority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            sets = df.to_dict('records')
            models = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
            instance = dataset.objects.get(id = request.GET['dataset'])
            return render(request, 'view_dataset.html',{
                'sets':sets,
                'dataset' : request.GET['dataset'],
                'models' : models,
                'datasetname' : instance.name,
                'budget' : instance.budget

            })
    else:
        return redirect('login')


def predict(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            modelid = request.POST['model']
            dsetid = request.POST['dataset']
            datapoints = data.objects.all().filter(dsid = dsetid).values()
            exists = False
            old = False
            dataset_instance = dataset.objects.get(id = dsetid)
            if(prediction.objects.filter(mid = modelid, did = datapoints[0]['id']).exists()):
                exists = True
                pred_instance =prediction.objects.get(mid = modelid, did = datapoints[0]['id'])
                if  dataset_instance.updated_at > pred_instance.created_at:
                    old = True
            
            if (exists == False or old == True):
                if(old):
                    prediction.objects.filter(mid = modelid ,dsid = dsetid).delete()
                    print('old stuff deleted')
                model1 = model.objects.get(id = modelid)
                settings = {'TCO' : model.TCO,
                'TVO': model1.TVO,
                'NET' : model1.NET,
                'PP' : model1.PP,
                'ROI' : model1.ROI,
                'CapEx' : model1.CapEx,
                'OneTime' : model1.OneTime,
                'OnGoing' : model1.OnGoing,
                'Revenue' : model1.Revenue,
                'Saving' : model1.Saving,
                'Avoid' : model1.Avoid,
                'Cost Grade' : model1.CostGrade,
                'Value Score' : model1.ValueScore,
                'Risk Score' : model1.RiskScore,
                'Blended Score' : model1.BlendedScore,
                'Calc Priority': model1.CalcPriority,
                'Overrided Priority' : model1.OverridedPriority
                }

                df = pd.DataFrame(datapoints)
                df1 = df.drop(df.columns[[0, 1, 2, 20]], axis = 1)
                for x in settings:
                    if settings[x] == 0:
                        df1 = df.drop(x, axis = 1)
                df1 = df1.fillna(0)
                x = df1.values #returns a numpy array
                min_max_scaler = preprocessing.MinMaxScaler()
                x_scaled = min_max_scaler.fit_transform(x)
                loadedmodel = tf.keras.models.load_model(model1.kfile)
                pred = loadedmodel.predict(x_scaled)
                
                df['pred'] = pred
                df_records = df.to_dict('records')
                model_instances = [prediction(
                    did =data.objects.get(id = record['id']),
                    mid =model1,
                    score = record['pred'],
                    dsid = dataset.objects.get(id = dsetid)

                        
                ) for record in df_records]
                prediction.objects.bulk_create(model_instances)

            df = pd.DataFrame(datapoints)

            df2 =  pd.DataFrame(prediction.objects.all().filter(mid = modelid, dsid = dsetid).values())
            df['score'] = df2['score']
            df = df.fillna("")
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            df = df.sort_values(by = ['score'], ascending = False)
            df_records1 = df.to_dict('records')
            models = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
            instance = dataset.objects.get(id = dsetid)
            return render(request, 'view_dataset.html',{
                'sets':df_records1,
                'dataset' : dsetid,
                'models' : models,
                'datasetname': instance.name,
                'budget': instance.budget

            })
        else:
            sets = dataset.objects.all().filter(user = request.user).values()
            return render(request, 'set_list.html',{
            'sets': sets
            })
    else:
        return redirect('login')


def models(request):
    if request.user.is_authenticated:
        sets = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
        return render(request, 'view_models.html',{
            'sets': sets
        })
    else:
        return redirect('login')

def cmodel(request):
    if request.user.is_authenticated:
        if request.method =="POST":
            df = pd.read_excel("static/data/training.xlsx")
            print(request.POST)
            settings = {'TCO' : request.POST['TCO'],
            'TVO': request.POST['TVO'],
            'NET' : request.POST['NET'],
            'PP' : request.POST['PP'],
            'ROI' : request.POST['ROI'],
            'CapEx' : request.POST['CapEx'],
            'OneTime' : request.POST['OneTime'],
            'OnGoing' : request.POST['OnGoing'],
            'Revenue' : request.POST['Revenue'],
            'Saving' : request.POST['Saving'],
            'Avoid' : request.POST['Avoid'],
            'Cost Grade' : request.POST['CostGrade'],
            'Value Score' : request.POST['ValueScore'],
            'Risk Score' : request.POST['RiskScore'],
            'Blended Score' : request.POST['BlendedScore'],
            'Calc Priority': request.POST['CalcPriority'],
            'Overrided Priority' : request.POST['OverridedPriority']
            }
            df['picked'] = [1 if x==4 else 0 for x in df['Overrided Priority']]
            for x in settings:
                if settings[x] == 0:
                    df = df.drop(x, axis = 1)

            x = df.values #returns a numpy array
            min_max_scaler = preprocessing.MinMaxScaler()
            x_scaled = min_max_scaler.fit_transform(x)
            df = pd.DataFrame(x_scaled)
            x_df = df.drop(df.shape[1]-1, axis = 1).values
            y_df = df[df.shape[1]-1].values

            X_train, X_test, Y_train, Y_test = train_test_split(x_df, y_df, test_size = 0.2)
            model1 = tf.keras.Sequential([
                tf.keras.Input(shape=(df.shape[1]-1,)),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(32, activation="relu"),
                tf.keras.layers.Dense(1, activation="sigmoid"),
            ])


            model1.compile(optimizer='adam',
                        loss='binary_crossentropy',
                        metrics=['accuracy'])
            history = model1.fit(X_train,
                                Y_train,
                                epochs =100,
                                validation_data= (X_test,Y_test),
                                verbose=0,
                            shuffle = False,
                            batch_size =64)
            acc = history.history['accuracy']
            val_acc = history.history.get('val_accuracy')[-1]
            import random
            model_location = "static/data/saved_models/"+str(request.user.username)+"_"+str(request.POST['modname'])+"_"+str(random.randrange(100,999,3))+".h5"
            model_location = model_location.replace(" ", "")
            model1.save(model_location)
            instance = model(user = request.user,
                name = request.POST['modname'],
                details = request.POST['description'],
                kfile = model_location,
                TCO = settings['TCO'], 
                TVO = settings['TVO'],
                NET= settings['NET'],
                PP = settings['PP'],
                ROI = settings['ROI'],
                CapEx = settings['CapEx'],
                OneTime= settings['OneTime'],
                OnGoing = settings['OnGoing'],
                Revenue = settings['Revenue'],
                Saving = settings['Saving'],
                Avoid = settings['Avoid'],
                CostGrade = settings['Cost Grade'],
                ValueScore = settings['Value Score'],
                RiskScore = settings['Risk Score'],
                BlendedScore = settings['Blended Score'],
                CalcPriority = settings['Calc Priority'],
                OverridedPriority = settings['Overrided Priority']) 
            
            instance.accuracy = val_acc*100
            instance.save()

        return redirect('/dash')
    else:
        return redirect('login')

def delete_dataset(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataset.objects.filter(id = dsid).delete()

        return redirect('dash')
    else:
        return redirect('login')

def delete_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataid = request.POST['dataid']
            data.objects.filter(id = dataid).delete()
            instance = dataset.objects.get(id = dsid)
            count = data.objects.filter(dsid = instance).count()
            instance.size = count
            instance.save()
            sets = data.objects.all().filter(dsid = dsid).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : dsid

            })
        return redirect('dash')
    else:
        return redirect('login')

def delete_model(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            mid = request.POST['model']
            instance = model.objects.get(id = mid)
            os.remove(instance.kfile)
            instance.delete()
        return redirect('dash')
    else:
        return redirect('login')

def edit_2(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            return redirect(dash)
        else:
            print('wtf is going on')
            print(request.GET)
            did = request.GET['dsid1']
            return render(request, 'edit.html',{
                'dataset' : did

            })
    else:
        return redirect('login')

def edit(request):
    print(request)
    if request.user.is_authenticated:
        if request.method=="POST":
            print(request.POST['dsid'])
        else:
            print(request.GET)
            did = request.GET['dsid']
            sets = data.objects.all().filter(dsid = did).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            sets = dumps(sets)
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : did

            })
    else:
        return redirect('login')

def dataList(request):
    sets = dataset.objects.all().filter(user = request.user).values()
    df = pd.DataFrame(sets)
    df = df[['id', 'name']]
    sets = df.to_dict('records')
    sets = dumps(sets)
    return JsonResponse(sets, safe=False)


def edit_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            did = request.POST['dataid']
            instance = data.objects.filter(id = did)
            instance.name = request.POST['NAME']
            instance.TCO = request.POST['TCO']
            instance.TVO =request.POST['TVO']
            instance.NET =request.POST['NET']
            instance.PP =request.POST['PP']
            instance.ROI =request.POST['ROI']
            instance.CapEx =request.POST['CapEx']
            instance.OneTime =request.POST['OneTime']
            instance.OnGoing =request.POST['OnGoing']
            instance.Revenue =request.POST['Revenue']
            instance.Saving =request.POST['Saving']
            instance.Avoid =request.POST['Avoid']
            instance.CostGrade =request.POST['Cost Grade']
            instance.ValueScore =request.POST['Value Score']
            instance.RiskScore =request.POST['Risk Score']
            instance.BlendedScore =request.POST['Blended Score']
            instance.CalcPriority =request.POST['Calc Priority']
            instance.OverridedPriority =request.POST['Overrided Priority']
            instance.accepted = request.POST['accepted']
            instance.save()


            test = dataset.objects.get(id = dsid)
            test.save()
    else:
        return redirect('login')


def add_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            instance = data(dsid = dsid,
            name = request.POST['NAME'],
            TCO = request.POST['TCO'],
            TVO =request.POST['TVO'],
            NET =request.POST['NET'],
            PP =request.POST['PP'],
            ROI =request.POST['ROI'],
            CapEx =request.POST['CapEx'],
            OneTime =request.POST['OneTime'],
            OnGoing =request.POST['OnGoing'],
            Revenue =request.POST['Revenue'],
            Saving =request.POST['Saving'],
            Avoid =request.POST['Avoid'],
            CostGrade =request.POST['Cost Grade'],
            ValueScore =request.POST['Value Score'],
            RiskScore =request.POST['Risk Score'],
            BlendedScore =request.POST['Blended Score'],
            CalcPriority =request.POST['Calc Priority'],
            OverridedPriority =request.POST['Overrided Priority'],
            accepted = request.POST['accepted'])
    else:
        return redirect('login')



        
def data_update( request):
    id = request.POST.get('row_id')
    x = request.POST.get('col_name')
    instance = data.objects.get(id = id)
    arr = request.POST.get('arr')
    instance.x = arr[x]
    instance.save()
    return JsonResponse({'data': 'worked'}, status =200)
@csrf_exempt
def edit_single_data(request):
        dataid = request.POST.get('row_id')
        datacolumn = request.POST.get('col_name')
        datavalue = request.POST.get('col_val')
        if (datavalue == ""):
            datavalue = None
        instance = data.objects.get(id = dataid)

        
        if(datacolumn == "name"):
            instance.name = datavalue
        elif(datacolumn == "TCO"):
            instance.TCO = datavalue
        elif(datacolumn == "TVO"):
            instance.TVO = datavalue
        elif(datacolumn == "NET"):
            instance.NET = datavalue
        elif(datacolumn == "PP"):
            instance.PP = datavalue
        elif(datacolumn == "ROI"):
            instance.ROI = datavalue
        elif(datacolumn == "CapEx"):
            instance.CapEx = datavalue
        elif(datacolumn == "OneTime"):
            instance.OneTime = datavalue
        elif(datacolumn == "OnGoing"):
            instance.OnGoing = datavalue
        elif(datacolumn == "Revenue"):
            instance.Revenue = datavalue
        elif(datacolumn == "Saving"):
            instance.Saving = datavalue
        elif(datacolumn == "Avoid"):
            instance.Avoid = datavalue
        elif(datacolumn == "CostGrade"):
            instance.CostGrade = datavalue
        elif(datacolumn == "ValueScore"):
            instance.ValueScore = datavalue
        elif(datacolumn == "RiskScore"):
            instance.RiskScore = datavalue
        elif(datacolumn == "BlendedScore"):
            instance.BlendedScore = datavalue
        elif(datacolumn == "CalcPriority"):
            instance.CalcPriority = datavalue
        elif(datacolumn == "OverridedPriority"):
            instance.OverridedPriority = datavalue
        

        instance.save()
        dsid = instance.dsid
        instance2 = dataset.objects.get(id = dsid.id)
        instance2.save()


        return JsonResponse({'status': True}, status = 200)


@csrf_exempt
def edit_whole_data(request):
        instance = data.objects.get(id = request.POST.get('row_id'))
        instance.name = request.POST.get('name')
        instance.TCO = request.POST.get('TCO')
        instance.TVO = request.POST.get('TVO')
        instance.NET = request.POST.get('NET')
        instance.PP = request.POST.get('PP')
        instance.ROI = request.POST.get("ROI")
        instance.CapEx = request.POST.get('CapEx')
        instance.OneTime = request.POST.get('OneTime')
        instance.OnGoing = request.POST.get('OnGoing')
        instance.Revenue = request.POST.get('Revenue')
        instance.Saving = request.POST.get('Saving')
        instance.Avoid = request.POST.get('Avoid')
        instance.CostGrade = request.POST.get('CostGrade')
        instance.ValueScore = request.POST.get('ValueScore')
        instance.RiskScore = request.POST.get('RiskScore')
        instance.BlendedScore = request.POST.get('BlendedScore')
        instance.CalcPriority = request.POST.get('CalcPriority')
        instance.OverridedPriority = request.POST.get('OverridedPriority')
        
        instance.save()
        dsid = instance.dsid
        instance2 = dataset.objects.get(id = dsid.id)
        instance2.save()

        
        return JsonResponse({'status': True}, status = 200)
@csrf_exempt
def delete_row(request):
    if request.method =='POST':
        did = request.POST['row_id']
        instance = data.objects.get(id = did)
        if(instance.delete()):
            dataset1 = dataset.objects.get(id = request.POST['dsid'])
            dataset1.save()
            return JsonResponse({'status':'success'}, safe=False)
        else:
            return JsonResponse({'status':'error'}, safe=False)
    else:
        raise Http404
        
def get_data(request):
    if request.method =='GET':
        dsid = request.GET['dsid']
        daata = data.objects.filter(dsid = dsid).values()
        df = pd.DataFrame(daata)
        df = df.fillna(0)
        sets = df.to_dict('records')
        sets = dumps(sets)
        return JsonResponse(sets, safe=False)
@csrf_exempt
def add_row(request):
    print(request.POST)
    dataset1 = dataset.objects.get(id = request.POST['dsid'])
    instance = data(dsid = dataset1, name= request.POST['name'],TVO= request.POST['tvo'],TCO= request.POST['tco'],NET= request.POST['net'],PP= request.POST['pp'],ROI= request.POST['roi'],CapEx= request.POST['capex'],OneTime= request.POST['onetime'],OnGoing= request.POST['ongoing'],Revenue= request.POST['revenue'],Saving= request.POST['saving'],Avoid= request.POST['avoid'],CostGrade= request.POST['costgrade'],ValueScore= request.POST['valuescore'],RiskScore= request.POST['riskscore'],BlendedScore= request.POST['blendedscore'],CalcPriority= request.POST['calcpriority'],OverridedPriority= request.POST['overridedpriority'],accepted=0)
    instance.save()
    dataset1.save()
    test= instance.id
    if(test != None):
        return JsonResponse({'status':'success'}, safe=False)
    else:
        return JsonResponse({'status':'error'}, safe=False)